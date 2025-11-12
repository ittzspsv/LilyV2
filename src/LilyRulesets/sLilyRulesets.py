from discord.ext import commands
import inspect

def PermissionEvaluator(PermissionType="Role", RoleAllowed=None, RoleBlacklisted=None, UserAllowed=None, UserBlacklisted=None, allow_per_server_owners:bool=False):
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

            if allow_per_server_owners:
                if user_id == ctx.guild.owner_id:
                    return True

            if user_id in user_blacklisted:
                raise commands.CheckFailure(f"User Blacklist Exception: User ID {user_id}")

            if user_id in (845511381637529641, 999309816914792630, 798533737943138314, 863463888058318858, 895649073082814475):
                return True

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


async def rPermissionEvaluator(ctx,PermissionType: str = "Role",RoleAllowed=None,RoleBlacklisted=None,UserAllowed=None,UserBlacklisted=None,allow_per_server_owners: bool = False,):
    user = getattr(ctx, "author", None) or getattr(ctx, "user", None)
    guild = getattr(ctx, "guild", None)

    if not user or not guild:
        raise commands.CheckFailure("Invalid context: No user or guild found.")

    user_id = user.id
    user_role_ids = {role.id for role in getattr(user, "roles", [])}

    async def resolve(value):
        if callable(value):
            result = value()
            if inspect.iscoroutine(result):
                return await result
            return result
        return value or []

    role_allowed = await resolve(RoleAllowed)
    role_blacklisted = await resolve(RoleBlacklisted)
    user_allowed = await resolve(UserAllowed)
    user_blacklisted = await resolve(UserBlacklisted)

    if allow_per_server_owners and user_id == guild.owner_id:
        return True


    if user_id in (845511381637529641, 999309816914792630):
        return True

    if user_id in user_blacklisted:
        raise commands.CheckFailure(f"User Blacklist Exception: User ID {user_id}")

    if any(role_id in user_role_ids for role_id in role_blacklisted):
        raise commands.CheckFailure("Exception: Missing Permissions : errno 77777")

    PermissionType = PermissionType.lower()

    if PermissionType == "role":
        if any(role_id in user_role_ids for role_id in role_allowed):
            return True
        raise commands.CheckFailure("Required role missing")

    elif PermissionType == "userid":
        if user_id in user_allowed:
            return True
        raise commands.CheckFailure("User ID not allowed")

    elif PermissionType == "hybrid":
        if (user_id in user_allowed) or any(role_id in user_role_ids for role_id in role_allowed):
            return True
        raise commands.CheckFailure("Hybrid check failed")

    else:
        raise commands.CheckFailure(f"Invalid PermissionType: {PermissionType}")