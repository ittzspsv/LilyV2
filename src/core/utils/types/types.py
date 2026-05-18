from enum import Enum, unique


@unique
class ChannelEnum(str, Enum):
    BF_WIN_LOSS = "bf_win_loss"
    BF_FRUIT_VALUES = "bf_fruit_values"
    LOGS_CHANNEL = "logs_channel"
    STAFF_UPDATES = "staff_updates"
    VALID_CHANNEL = "valid_channel"

@unique
class CommandEnum(str, Enum):
    STAFF_DATA = "staff_data"
    STAFF_LIST = "staff_list"

    STRIKE_ADD = "strike_add"
    STRIKE_REMOVE = "strike_remove"
    STRIKE_EDIT = "strike_edit"
    STRIKE_SHOW = "strike_show"

    STAFF_EDIT = "staff_edit"
    STAFF_SELF_EDIT = "staff_self_edit"

    STAFF_ADD = "staff_add"
    STAFF_ADD_BATCH = "staff_add_batch"
    STAFF_REMOVE = "staff_remove"
    STAFF_REMOVE_RAW = "staff_remove_raw"

    STAFF_ROLES = "staff_roles"
    DEV_STAFF_UPDATE = "dev_staff_update"

    LOA_ADD = "loa_add"
    LOA_REMOVE = "loa_remove"

    RANK_PROMOTE = "rank_promote"
    RANK_PROMOTE_BATCH = "rank_promote_batch"
    RANK_DEMOTE = "rank_demote"

    QUOTA_ADD = "quota_add"
    QUOTA_LIST = "quota_list"
    QUOTA_REMOVE = "quota_remove"
    QUOTA_CHECK = "quota_check"
    QUOTA_EVALUATE = "quota_evaluate"

    STAFF_ROLE_REMOVE = "staff_role_remove"
    STAFF_ROLE_REMOVE_RAW = "staff_role_remove_raw"

    BAN = "ban"
    UNBAN = "unban"
    WARN = "warn"
    UNMUTE = "unmute"

    MS = "ms"
    MODLOGS = "modlogs"
    MODERATION_INSIGHTS = "moderation_insights"

    CASE_EDIT = "case_edit"
    CASE_EDIT_ABSOLUTE = "case_edit_absolute"
    CASE_DELETE = "case_delete"
    CASE_ATTACH = "case_attach"
    CASE_PROOFS = "case_proofs"


    QUEUE = "queue"
    QUEUE_REMOVE = "queue_remove"

    TICKET_CLOSE = "ticket_close"
    TICKET_RENAME = "ticket_rename"
    TICKET_ADD = "ticket_add"

    PURGE = "purge"
    SET_PREFIX = "set_prefix"
    ROLE = "role"
    AFK = "afk"