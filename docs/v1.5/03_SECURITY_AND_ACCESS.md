# Security & Access – SPIP v1.5

## Purpose

This document defines the additional security requirements introduced in SPIP v1.5.

Existing security architecture from SPIP v1.0 remains unchanged unless specified below.

---

# Authentication

Authentication mechanism remains unchanged.

Supported authentication:

- JWT Authentication
- Role Based Access Control (RBAC)

---

# Authorization

The following permissions are introduced.

| Module | Planner | Manager | Admin |
|---------|----------|----------|--------|
| FG Workspace | Read | Read | Read/Write |
| BOM | Read | Read | Read |
| Dependency Analysis | Read | Read | Read |
| Dashboard | Read | Read | Configure |
| Reports | Read | Export | Manage |

---

# BOM Security

BOM information is read-only.

Users cannot:

- Add BOM
- Edit BOM
- Delete BOM

BOM synchronization is controlled by SAP integration.

---

# Planning Security

Only authorized users may:

- Execute planning
- Trigger allocation
- Approve planning results

---

# Audit Logging

The following activities shall be logged.

- Planning execution
- Allocation approval
- Report generation
- Configuration changes
- User login

---

# Data Protection

Sensitive information shall never be exposed through APIs.

Examples:

- Passwords
- Tokens
- Internal configuration
- Database credentials

---

# Future Enhancements (V2)

- SSO Integration
- MFA
- Approval Workflow
- Digital Signatures
- Fine-grained Permissions