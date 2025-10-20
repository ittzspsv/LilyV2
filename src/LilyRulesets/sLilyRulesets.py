from discord.ext import commands
import inspect

def PermissionEvaluator(PermissionType="Role", RoleAllowed=None, RoleBlacklisted=None, UserAllowed=None, UserBlacklisted=None):
    def decorator(func):
        async def predicate(ctx: commands.Context):
            user_id = ctx.author.id
            user_role_ids = {role.id for role in ctx.author.roles}

            async def maybe_call(obj):
                if callable(obj):
                    result = obj()
                    if hasattr(result, "__await__"):
                        return await result
                    return result
                return obj or []

            role_allowed = await maybe_call(RoleAllowed)
            role_blacklisted = await maybe_call(RoleBlacklisted)
            user_allowed = await maybe_call(UserAllowed)
            user_blacklisted = await maybe_call(UserBlacklisted)

            if user_id in user_blacklisted:
                raise commands.CheckFailure(f"User Blacklist Exception: User ID {user_id}")

            #if user_id in (845511381637529641, 999309816914792630):
                #return True

            if any(role_id in user_role_ids for role_id in role_blacklisted):
                raise commands.CheckFailure(f"Exception: Missing Permissions : errno 77777")

            if PermissionType.lower() == "role":
                if any(role_id in user_role_ids for role_id in role_allowed):
                    return True
                raise commands.CheckFailure("Required role missing")
            elif PermissionType.lower() == "userid":
                if user_id in user_allowed:
                    return True
                raise commands.CheckFailure("User ID not allowed")
            elif PermissionType.lower() == "hybrid":
                if (user_id in user_allowed) or (any(role_id in user_role_ids for role_id in role_allowed)):
                    return True
                raise commands.CheckFailure("Hybrid check failed")
            else:
                raise commands.CheckFailure(f"Invalid PermissionType: {PermissionType}")

        return commands.check(predicate)(func)
    return decorator
async def rPermissionEvaluator(ctx, PermissionType: str = "Role", RoleAllowed=None, RoleBlacklisted=None, UserAllowed=None, UserBlacklisted=None):
    user_id = ctx.author.id
    user_role_ids = {role.id for role in ctx.author.roles}


    async def resolve(value):
        if callable(value):
            if inspect.iscoroutinefunction(value):
                return await value()
            else:
                return value()
        return value or []

    RoleAllowed = await resolve(RoleAllowed)
    RoleBlacklisted = await resolve(RoleBlacklisted)
    UserAllowed = await resolve(UserAllowed)
    UserBlacklisted = await resolve(UserBlacklisted)

    # Blacklist checks
    if user_id in UserBlacklisted:
        return False

    if any(role_id in user_role_ids for role_id in RoleBlacklisted):
        return False


    PermissionType = PermissionType.lower()
    if PermissionType == "role":
        return any(role_id in user_role_ids for role_id in RoleAllowed)
    elif PermissionType == "userid":
        return user_id in UserAllowed
    elif PermissionType == "hybrid":
        return (user_id in UserAllowed) or any(role_id in user_role_ids for role_id in RoleAllowed)
    else:
        return False