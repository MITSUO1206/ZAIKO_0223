"""ドメインEnum（Excel仕様準拠）"""
import enum


class Role(str, enum.Enum):
    USER = "USER"
    APPROVER = "APPROVER"
    ADMIN = "ADMIN"


class LedgerType(str, enum.Enum):
    INBOUND = "INBOUND"     # 入庫
    OUTBOUND = "OUTBOUND"   # 出庫
    ISSUE = "ISSUE"         # 払い出し
    DISPOSAL = "DISPOSAL"   # 廃棄


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    APPROVE = "APPROVE"
