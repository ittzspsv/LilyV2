from discord.ext import commands


def PermissionEvaluator(PermissionType: str = "Role",RoleAllowed=None,RoleBlacklisted=None,UserAllowed=None,UserBlacklisted=None):
    def predicate(ctx:commands.Context):
        user_id = ctx.author.id
        user_role_ids = {role.id for role in ctx.author.roles}

        role_allowed = RoleAllowed() if callable(RoleAllowed) else RoleAllowed or []
        role_blacklisted = RoleBlacklisted() if callable(RoleBlacklisted) else RoleBlacklisted or []
        user_allowed = UserAllowed() if callable(UserAllowed) else UserAllowed or []
        user_blacklisted = UserBlacklisted() if callable(UserBlacklisted) else UserBlacklisted or []

        if ctx.author.id == ctx.guild.owner_id:
            return True


        if user_id in user_blacklisted:
            raise commands.CheckFailure(f"User Blacklist Exception: User ID {user_id}")

        if any(role_id in user_role_ids for role_id in role_blacklisted):
            raise commands.CheckFailure(f"Exception: Missing Permissions : errno 77777")

        if PermissionType.lower() == "role":
            if any(role_id in user_role_ids for role_id in role_allowed):
                return True
            else:
                raise commands.CheckFailure("Required role missing")

        elif PermissionType.lower() == "userid":
            if user_id in user_allowed:
                return True
            else:
                raise commands.CheckFailure("User ID not allowed")

        elif PermissionType.lower() == "hybrid":
            if (user_id in user_allowed) or (any(role_id in user_role_ids for role_id in role_allowed)):
                return True
            else:
                raise commands.CheckFailure("Hybrid check failed")

        else:
            raise commands.CheckFailure(f"Invalid PermissionType: {PermissionType}")

    return commands.check(predicate)

def rPermissionEvaluator(ctx,PermissionType: str = "Role",RoleAllowed = [],RoleBlacklisted = [],UserAllowed = [],UserBlacklisted = []):
    user_id = ctx.author.id
    user_role_ids = {role.id for role in ctx.author.roles}
    
    RoleAllowed = RoleAllowed() if callable(RoleAllowed) else RoleAllowed
    RoleBlacklisted = RoleBlacklisted() if callable(RoleBlacklisted) else RoleBlacklisted
    UserAllowed = UserAllowed() if callable(UserAllowed) else UserAllowed
    UserBlacklisted = UserBlacklisted() if callable(UserBlacklisted) else UserBlacklisted

    if ctx.author.id == ctx.guild.owner_id:
        return True

    if user_id in UserBlacklisted:
        return False

    if any(role_id in user_role_ids for role_id in RoleBlacklisted):
        return False

    if PermissionType.lower() == "role":
        return any(role_id in user_role_ids for role_id in RoleAllowed)

    elif PermissionType.lower() == "userid":
        return user_id in UserAllowed

    elif PermissionType.lower() == "hybrid":
        return (user_id in UserAllowed) or any(role_id in user_role_ids for role_id in RoleAllowed)

    else:
        return False