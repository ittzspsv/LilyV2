from enum import Enum

class RoleType(str, Enum):
        Staff = "Staff"
        Responsibility = "Responsibility"

class OnQuotaEvent(str, Enum):
        Promote = "Promote"
        Demote = "Demote"
        Strike = "Strike"
        none = "None"

class QuotaCheckBy(str, Enum):
        DailyCheck = "1d"
        WeeklyCheck = "7d"
        MonthlyCheck = "30d"