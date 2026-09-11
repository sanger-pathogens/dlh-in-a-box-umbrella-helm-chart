"""Assign DataHub roles from OIDC-provisioned group membership.

DataHub provisions a group per value of the OIDC roles claim but never
derives a role from it. This action closes that gap: every write of a
user's groupMembership aspect (which is what an OIDC login performs) is
re-read from GMS and turned into an assign or unassign of the mapped role.

Loaded into a ConfigMap by templates/datahub-group-role-sync-configmap.yaml
and run by the datahub-actions component. The recipe next to it in that
ConfigMap carries the group-to-role map, which the chart derives from
global.identity.accessRoles.
"""

from __future__ import annotations

import logging

from datahub_actions.action.action import Action
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.pipeline.pipeline_context import PipelineContext

logger = logging.getLogger(__name__)

MCL_EVENT_TYPE = "MetadataChangeLogEvent_v1"
GROUP_MEMBERSHIP_ASPECT = "groupMembership"

# One query for both sides of the decision, so there is no window where
# groups and role are read from different points in time.
USER_STATE_QUERY = """
query userState($urn: String!) {
  corpUser(urn: $urn) {
    urn
    groups: relationships(input: {types: ["IsMemberOfGroup"], direction: OUTGOING, start: 0, count: 200}) {
      relationships { entity { urn } }
    }
    roles: relationships(input: {types: ["IsMemberOfRole"], direction: OUTGOING, start: 0, count: 10}) {
      relationships { entity { urn } }
    }
  }
}
"""

LIST_USERS_QUERY = """
query listUsers($start: Int!, $count: Int!) {
  listUsers(input: {start: $start, count: $count}) {
    total
    users { urn }
  }
}
"""

# roleUrn is nullable, and passing null is how DataHub unassigns a role.
ASSIGN_ROLE_MUTATION = """
mutation assignRole($role: String, $actors: [String!]!) {
  batchAssignRole(input: {roleUrn: $role, actors: $actors})
}
"""


def _related_urns(user: dict, key: str) -> list[str]:
    relationships = ((user.get(key) or {}).get("relationships")) or []
    return [
        rel["entity"]["urn"]
        for rel in relationships
        if (rel or {}).get("entity", {}).get("urn")
    ]


class GroupRoleSyncAction(Action):
    @classmethod
    def create(cls, config_dict: dict, ctx: PipelineContext) -> GroupRoleSyncAction:
        return cls(config_dict or {}, ctx)

    def __init__(self, config: dict, ctx: PipelineContext) -> None:
        if ctx.graph is None:
            raise ValueError(
                "group_role_sync needs a graph client: add a `datahub:` block to the recipe."
            )
        self.graph = ctx.graph.graph
        # One DataHub role per group, because DataHub holds one role per user.
        self.group_role_map: dict[str, str] = config.get("group_role_map") or {}
        self.role_precedence: list[str] = config.get("role_precedence") or []
        self.admin_role: str = config.get("admin_role") or "urn:li:dataHubRole:Admin"
        self.always_admin = set(config.get("always_admin") or [])
        self.demote_unmapped: bool = bool(config.get("demote_unmapped", True))
        logger.info(
            "group_role_sync: %d mapped group(s), demote_unmapped=%s, always_admin=%s",
            len(self.group_role_map),
            self.demote_unmapped,
            sorted(self.always_admin),
        )
        if config.get("reconcile_on_start", True):
            self._sweep()

    def act(self, event: EventEnvelope) -> None:
        if event.event_type != MCL_EVENT_TYPE:
            return
        mcl = event.event
        entity_type = str(getattr(mcl, "entityType", "") or "").lower()
        # Only groupMembership. Assigning a role writes roleMembership on the
        # same entity, which produces another corpuser event -- reacting to
        # that too would make the action feed on its own writes.
        if entity_type != "corpuser":
            return
        if getattr(mcl, "aspectName", None) != GROUP_MEMBERSHIP_ASPECT:
            return
        user_urn = getattr(mcl, "entityUrn", None)
        if user_urn:
            self._reconcile_user(user_urn)

    def _desired_role(self, user_urn: str, group_urns: list[str]) -> str | None:
        if user_urn in self.always_admin:
            return self.admin_role
        # A user may belong to several mapped groups -- holding both
        # platform-admin and platform-user is normal -- while DataHub holds
        # one role per user, so the strongest candidate wins.
        candidates = {
            self.group_role_map[group_urn]
            for group_urn in group_urns
            if group_urn in self.group_role_map
        }
        for role_urn in self.role_precedence:
            if role_urn in candidates:
                return role_urn
        return None

    def _reconcile_user(self, user_urn: str) -> None:
        try:
            state = self.graph.execute_graphql(USER_STATE_QUERY, {"urn": user_urn})
            user = (state or {}).get("corpUser") or {}
            groups = _related_urns(user, "groups")
            current_roles = _related_urns(user, "roles")
            current = current_roles[0] if current_roles else None
            desired = self._desired_role(user_urn, groups)

            if desired == current:
                return
            if desired is None and not self.demote_unmapped:
                return

            self.graph.execute_graphql(
                ASSIGN_ROLE_MUTATION, {"role": desired, "actors": [user_urn]}
            )
            logger.info(
                "group_role_sync: %s role %s -> %s (groups=%s)",
                user_urn,
                current,
                desired,
                groups,
            )
        except Exception:
            # Never take the pipeline down for one user; the next login event
            # or the next startup sweep retries.
            logger.exception("group_role_sync: failed to reconcile %s", user_urn)

    def _sweep(self) -> None:
        start, count, seen = 0, 100, 0
        try:
            while True:
                page = self.graph.execute_graphql(
                    LIST_USERS_QUERY, {"start": start, "count": count}
                )
                listing = (page or {}).get("listUsers") or {}
                users = listing.get("users") or []
                for user in users:
                    if user.get("urn"):
                        self._reconcile_user(user["urn"])
                        seen += 1
                start += count
                if not users or start >= int(listing.get("total") or 0):
                    break
            logger.info("group_role_sync: startup sweep reconciled %d user(s)", seen)
        except Exception:
            logger.exception("group_role_sync: startup sweep failed")

    def close(self) -> None:
        return None
