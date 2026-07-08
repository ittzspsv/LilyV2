## Introduction

- This guide shows you how to use lily and It's commands in detail

## How to read this guide

- Each commands that are mentioned on that guide has no prefix. The bot allows you to set your custom prefix (individual) and the global prefix (.)
- Slash commands are recommended and preferred by discord, So every commands are represented using slash commands only.

Repr.
<member>: Can be either <@1488556914605428988> or spshree or 1516297235384762489 [dev_id]

- Other representations are directly stated.
- Parameters wrapped in `[]` are **optional**.
- Parameters wrapped in `<>` are **required**.

HIgher Staffs include : Administrators and Above
Management Team : Management and above.
Developer : Super user (Has access to all commands and restricted commands (that can break the bot entirely.))

# Moderation System Command Hierarchy

## Basic Commands

| Command      | Aliases          | Parameters                     | Permission    | Description                              | Example                                      |
| ------------ | ---------------- | ------------------------------ | ------------- | ---------------------------------------- | -------------------------------------------- |
| `warn`       | —                | `<member> <reason>`            | Staff         | Warn a user.                             | `warn @spshree Spamming in general chat`     |
| `mute`       | —                | `<member> <duration> <reason>` | Staff         | Timeout a user for a specified duration. | `mute @spshree 1h Excessive caps lock usage` |
| `unmute`     | —                | `<member> <reason>`            | Staff         | Remove a user's timeout.                 | `unmute @spshree Timeout period served`      |
| `ban`        | —                | `<member> <reason>`            | Higher Staffs | Ban a user from the server.              | `ban @spshree Reason goes here.....`         |
| `unban`      | —                | `<user_id> <reason>`           | Staff         | Unban a previously banned user.          | `unban 123456789012345678 Appeal accepted`   |
| `quarantine` | `jail`, `j`, `q` | `<member> <reason>`            | Staff         | Place a user into quarantine (jail).     | `quarantine @spshree Suspicious activity`    |
| `release`    | `qr`, `r`        | `<member> <reason>`            | Staff         | Release a user from quarantine.          | `release @spshree Cleared after review`      |

## Moderator Commands (mod)

| Command        | Parameters                         | Permission | Description                                                                               | Example                  |
| -------------- | ---------------------------------- | ---------- | ----------------------------------------------------------------------------------------- | ------------------------ |
| `mod stats`    | `[member] [page_start] [page_end]` | Staff      | Display moderation statistics for yourself or another moderator.                          | `mod stats @spshree 1 5` |
| `mod insights` | —                                  | Staff      | Show moderation insights, including a leaderboard and a 30-day moderation activity graph. | `mod insights`           |

## Case Management (case)

| Command              | Parameters                                            | Permission    | Description                                          | Example                                     |
| -------------------- | ----------------------------------------------------- | ------------- | ---------------------------------------------------- | ------------------------------------------- |
| `case list`          | `[member] [type] [page_start] [page_end] [moderator]` | Staff         | Display moderation cases with optional filters.      | `case list @spshree ban 1 10`               |
| `case edit`          | `<case_id> <new_reason>`                              | Staff         | Edit the reason for one of your own cases.           | `case edit 452 Updated reason after review` |
| `case edit_absolute` | `<case_id> <new_reason>`                              | Higher Staffs | Edit any moderation case.                            | `case edit_absolute 452 Corrected by admin` |
| `case delete`        | `<case_id>`                                           | Staff         | Delete a moderation case.                            | `case delete 452`                           |
| `case attach`        | —                                                     | Staff         | Attach image or video evidence to a moderation case. | `case attach` (with file upload)            |
| `case proofs`        | `<case_id>`                                           | Staff         | View all evidence attached to a moderation case.     | `case proofs 452`                           |

## Moderation Acronyms (mod)

| Command                | Parameters      | Permission     | Description                                                    | Example                                         |
| ---------------------- | --------------- | -------------- | -------------------------------------------------------------- | ----------------------------------------------- |
| `mod acronym_add`      | `<key> <value>` | Staff          | Create a personal moderation acronym.                          | `mod acronym_add nsfw Not Safe For Work`        |
| `mod acronym_remove`   | `<key>`         | Staff          | Remove one of your moderation acronyms.                        | `mod acronym_remove nsfw`                       |
| `mod acronym_update`   | `<key> <value>` | Staff          | Update an existing moderation acronym.                         | `mod acronym_update nsfw Not Suitable For Work` |
| `mod acronyms`         | —               | Staff          | List all of your saved moderation acronyms.                    | `mod acronyms`                                  |
| `mod acronym_transfer` | `<member>`      | Developer Only | Transfer all of your moderation acronyms to another moderator. | `mod acronym_transfer @spshree`                 |

# Management System Command Hierarchy

## Staff System

| Command            | Parameters                                                  | Permission      | Description                                      | Example                                                   |
| ------------------ | ----------------------------------------------------------- | --------------- | ------------------------------------------------ | --------------------------------------------------------- |
| `staff data`       | `[member]`                                                  | Staff           | Display information about a staff member.        | `staff data @spshree`                                     |
| `staff list`       | —                                                           | Staff           | List all staff members.                          | `staff list`                                              |
| `staff add`        | `<member>`                                                  | Management Only | Add a staff member.                              | `staff add @spshree`                                      |
| `staff add_batch`  | `<staff_ids>`                                               | Management Only | Add multiple staff members at once.              | `staff add_batch 123456789012345678,234567890123456789`   |
| `staff remove`     | `<member> <reason>`                                         | Management Only | Remove a staff member.                           | `staff remove @spshree Inactive for 60 days`              |
| `staff remove_raw` | `<staff_id> <reason>`                                       | Management Only | Remove a staff member using their dev ID.        | `staff remove_raw 123456789012345678 Left the server`     |
| `staff edit`       | `<staff_id> [name] [joined_on] [timezone] [responsibility]` | Management Only | Edit a staff member's information.               | `staff edit 123456789012345678 name=spshree timezone=IST` |
| `staff self_edit`  | `[name] [timezone]`                                         | Staff           | Update your own staff profile.                   | `staff self_edit name=spshree timezone=IST`               |
| `staff roles`      | —                                                           | Staff           | List all configured staff roles.                 | `staff roles`                                             |
| `staff coverage`   | —                                                           | Staff           | Display timezone coverage for all staff members. | `staff coverage`                                          |

## Staff Infractions

- Infraction includes strikes, warnings, verbal warning all embedded into a single key term.

| Command             | Parameters                     | Permission        | Description                              | Example                                      |
| ------------------- | ------------------------------ | ----------------- | ---------------------------------------- | -------------------------------------------- |
| `infraction issue`  | `<member>`                     | Higher Staff Only | Issue an infraction to a staff member.   | `infraction issue @spshree`                  |
| `infraction remove` | `<infraction_id>`              | Higher Staff Only | Remove an infraction.                    | `infraction remove 78`                       |
| `infraction edit`   | `<infraction_id> <new_reason>` | Higher Staff Only | Update an infraction's reason.           | `infraction edit 78 Downgraded after appeal` |
| `infraction show`   | `<member>`                     | Staff             | List all infractions for a staff member. | `infraction show @spshree`                   |

## Leave of Absence (LOA)

| Command       | Parameters          | Permission        | Description                              | Example                                      |
| ------------- | ------------------- | ----------------- | ---------------------------------------- | -------------------------------------------- |
| `loa add`     | `<member> <reason>` | Higher Staff Only | Give a Leave of Absence (LOA).           | `loa add @spshree Family emergency, 2 weeks` |
| `loa request` | —                   | Staffs            | Create an LOA request for approval.      | `loa request`                                |
| `loa show`    | `[member]`          | Staffs            | Display active Leave of Absence records. | `loa show @spshree`                          |
| `loa remove`  | `<member>`          | Higher Staff Only | End a member's Leave of Absence.         | `loa remove @spshree`                        |
| `loa delete`  | `<leave_id>`        | Higher Staff Only | Delete an LOA record.                    | `loa delete 34`                              |

## Rank Management

| Command              | Parameters          | Permission      | Description                             | Example                                        |
| -------------------- | ------------------- | --------------- | --------------------------------------- | ---------------------------------------------- |
| `rank promote`       | `<member> <reason>` | Management Only | Promote a staff's rank.                 | `rank promote @spshree Consistent performance` |
| `rank promote_batch` | `<query>`           | Management Only | Promote multiple staff members at once. | `rank promote_batch role:trial-mod`            |
| `rank demote`        | `<member> <reason>` | Management Only | Demote a staff member.                  | `rank demote @spshree Policy violation`        |
| `rank configure`     | —                   | Management Only | Configure the server's rank hierarchy.  | `rank configure`                               |

## Quota Management

| Command          | Parameters                                                                 | Permission | Description                                                       | Example                                              |
| ---------------- | -------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------- | ---------------------------------------------------- |
| `quota add`      | `<role> <minimum_ms> <minimum_msg> <pass_action> <fail_action> <check_by>` | Management | Define a quota for a staff role.                                  | `quota add @Moderator 3600000 50 none demote weekly` |
| `quota list`     | —                                                                          | Staff      | List all defined quotas.                                          | `quota list`                                         |
| `quota remove`   | `<quota_id>`                                                               | Management | Remove a quota.                                                   | `quota remove 5`                                     |
| `quota check`    | `[member]`                                                                 | Staff      | Check a staff member's quota progress.                            | `quota check @spshree`                               |
| `quota evaluate` | `<role>`                                                                   | Management | Evaluate quota performance for all staff with the specified role. | `quota evaluate @Moderator`                          |
