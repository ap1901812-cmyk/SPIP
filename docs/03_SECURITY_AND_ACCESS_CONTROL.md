# 03 — Security & Access Control
Supply Planning Intelligence Platform (SPIP)
Purpose: Define mandatory security requirements for SPIP . These controls must be implemented,
tested, and must not be weakened for development convenience.
### 1. Security Principles
SPIP shall follow:
Security by design
Least privilege
Deny by default
Defense in depth
Zero trust between application boundaries
Secure defaults
Complete auditability for sensitive actions
Frontend restrictions are never a substitute for backend authorization.
### 2. Authentication
All protected functionality requires authenticated access.
Requirements:
Secure login mechanism
Strong password policy
Passwords stored using a modern password-hashing algorithm
Secure access and refresh-token/session handling
Token/session expiration
Logout and session revocation
Password reset using short-lived, single-use credentials
Optional/required MFA depending on role and enterprise policy
No passwords or authentication secrets in logs
Administrative accounts require stronger controls.
Exact authentication technology will be selected in the TRD.
### 3. Authorization & RBAC
Access shall use server-side Role-Based Access Control.
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•

Initial roles:
Enterprise Administrator
Planner
Procurement User
Approver/Manager
Read-Only/Reporting User
Service/Integration Identity
Every protected API must verify permissions.
Example:
User
 ↓
Authentication
 ↓
Identity
 ↓
Role + Permission Check
 ↓
Authorized? ── No → 403
 ↓ Yes
Business Operation
Users shall receive only the minimum permissions required for their work.
### 4. Rate Limiting
Rate limits shall vary by endpoint risk.
Authentication endpoints
Login, password reset and similar endpoints require stricter controls using:
per-IP limits;
per-account limits;
exponential backoff;
abuse monitoring.
Avoid permanent/hard account lockouts that can themselves be abused for denial-of-service attacks.
Other APIs
Moderate limits for public/untrusted endpoints
Appropriate higher limits for authenticated business operations
Separate limits for computationally expensive operations where necessary
All thresholds must be configurable, not hardcoded.
•
•
•
•
•
•
•
•
•
•
•
•
•

Rate limiting must work correctly across multiple application instances behind the load balancer .
### 5. Strict Input Validation
Every untrusted input must be validated against an explicit schema.
Validate as applicable:
type;
length;
range;
format;
allowed values;
required fields;
identifiers;
dates;
quantities;
uploaded files.
Invalid input must be rejected, not merely escaped or sanitized.
Backend validation remains mandatory even when frontend validation exists.
Database operations shall use safe parameterized/ORM query mechanisms.
### 6. Secrets Management
The complete repository shall be scanned for:
API keys;
passwords;
access tokens;
database credentials;
private keys;
other secrets.
Secrets must:
never be hardcoded;
never be committed to Git;
never be exposed to the frontend unless explicitly designed as non-secret public configuration;
be supplied through approved environment/secret-management mechanisms;
be different across environments where appropriate.
.env files containing real secrets must not be committed.
Example configuration files may contain placeholders only.
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•

Automated secret scanning should be part of CI/CD.
If a secret is accidentally committed, deleting the line is insufficient — the credential must be
considered for immediate rotation/revocation.
### 7. Dependency Security
Backend, frontend, ML and infrastructure dependencies shall be audited for known vulnerabilities.
The process shall:
scan dependencies;
identify known vulnerabilities;
record severity;
determine exploitability/relevance;
safely update or replace affected packages;
run regression tests.
Dependency scanning should run automatically in CI/CD.
Dependency versions shall be reproducible using appropriate lockfiles.
Critical/high-risk vulnerabilities must not be knowingly ignored without documented risk acceptance.
### 8. Error Handling & Information Leakage
Users must never receive:
stack traces;
raw SQL/database errors;
internal filesystem paths;
secrets;
tokens;
infrastructure credentials;
unnecessary implementation details.
Example client response:
Unable to complete the request.
Reference ID: REQ-8F21
Full technical information should instead be recorded securely server-side.
Logs must themselves avoid sensitive-data leakage.
1.
2.
3.
4.
5.
6.
•
•
•
•
•
•
•

### 9. File Upload Security
If SPIP accepts files, validate:
permitted file type;
MIME/content;
size;
structure where practical;
authorization.
Do not trust filename extensions alone.
Uploads must:
use safe/randomized stored names where appropriate;
be stored outside directly executable application locations;
never be executable as application code;
be isolated from application binaries;
be safely parsed;
be malware-scanned where enterprise policy requires it.
Rejected files must not remain accessible.
### 10. API Security
Protected APIs shall require both:
Authentication
      +
Authorization
Additional requirements:
HTTPS in production
Strict request validation
Controlled CORS
Safe HTTP methods
Request-size limits
Rate limiting
Pagination/limits for large queries
Safe error responses
Idempotency where business operations require it
The reference project's unrestricted CORS configuration must not be retained.
Allowed origins shall be explicitly configured per environment.
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•

### 11. Database Security
Database requirements:
no public database exposure unless explicitly required and secured;
dedicated application credentials;
least-privilege database permissions;
encrypted connections where appropriate;
safe queries;
database constraints;
controlled migrations;
backups;
tested recovery procedures.
Application users shall not receive direct database credentials.
Production credentials shall differ from development credentials.
### 12. Encryption
Sensitive traffic shall be encrypted in transit using modern TLS.
Sensitive stored information shall use appropriate encryption at rest according to data classification and
infrastructure capabilities.
Passwords must be hashed, not reversibly encrypted.
Encryption keys must be managed separately from encrypted data where practical.
### 13. Session & Token Security
Authentication credentials/tokens must:
expire;
be securely generated;
be revocable where required;
use appropriate secure storage;
never appear in URLs;
never be written to application logs.
Refresh-token/session rotation and reuse detection should be implemented where applicable.
Browser storage strategy shall be selected based on the final authentication architecture and CSRF/XSS
threat model.
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•

### 14. Frontend Security
The frontend must:
never contain backend secrets;
never trust hidden/disabled buttons as authorization;
avoid unsafe HTML rendering;
handle tokens/sessions securely;
follow appropriate browser security policies;
avoid exposing unnecessary sensitive business data.
Server-side authorization remains authoritative.
### 15. Audit Logging
Important actions shall generate immutable or appropriately protected audit records.
Examples:
login events;
failed authentication;
permission changes;
user/role changes;
allocation creation/modification;
approvals;
sensitive configuration changes;
security events.
Audit records should capture:
Who
What
When
Result
Relevant target/resource
Request/Correlation ID
Passwords, tokens and secrets must never be included.
### 16. Administrative Security
Enterprise Administrator access is highly privileged.
Requirements include:
stronger authentication;
MFA where required;
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•

least privilege;
explicit administrative permissions;
detailed audit logging;
protection against privilege escalation.
An administrator should not automatically bypass every business control unless explicitly required.
### 17. Security Headers & Browser Protection
Production web responses shall use appropriate protections such as:
Content Security Policy where applicable;
anti-clickjacking controls;
MIME-sniffing protection;
secure cookie attributes;
appropriate referrer policy.
Exact configuration will depend on deployment architecture.
### 18. Security Monitoring
Security-relevant events should be observable.
Examples:
repeated failed logins;
unusual rate-limit activity;
authorization failures;
suspicious upload attempts;
unexpected administrative actions;
application security errors.
Critical security events should support alerting.
### 19. Production Configuration
Development shortcuts must not silently reach production.
Production must disable or restrict:
debug mode;
verbose error output;
development credentials;
unrestricted CORS;
unnecessary development endpoints;
unsafe test accounts.
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•

Configuration shall be environment-specific.
### 20. Security Testing
Before production release, perform:
authentication tests;
authorization/RBAC tests;
input-validation tests;
rate-limit tests;
dependency vulnerability scan;
secret scan;
file-upload security tests where applicable;
API security tests;
configuration review;
security-focused integration tests.
Security tests shall also run in CI/CD where practical.
### 21. Critical Release Blockers
Production release must be blocked for unresolved critical issues such as:
authentication bypass;
authorization bypass;
hardcoded production credentials;
exposed secrets;
exploitable critical dependency vulnerability;
SQL injection;
arbitrary code/file execution;
unrestricted administrative access;
sensitive data exposure.
High-severity findings require remediation or formally documented risk acceptance according to
enterprise policy.
### 22. AI Development Rule
When Claude implements security-sensitive functionality:
Read SECURITY.md
      ↓
Read relevant feature ticket
      ↓
Implement control
      ↓
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•

Write security tests
      ↓
Run tests/scanners
      ↓
Report results
Claude must never remove or weaken a security control merely to make development easier or to make
a failing test pass.
Any proposed security-design change must be explicitly identified before implementation.
### 23. Security Source of Truth
This document is the authoritative high-level security contract for SPIP .
Detailed implementation choices — authentication libraries, rate-limit storage, secret-management
technology, deployment security tooling, etc. — shall be selected in the TRD and Architecture
documents.
Security takes priority over convenience.
End of Security & Access Control Specification

## Export and SAP Integration Security

- Report generation/download requires authentication and RBAC authorization.
- Export queries must enforce the user's authorized plant/data scope on the backend; frontend filters are not a security boundary.
- Exported files must not expose secrets or fields the user is not authorized to view.
- Large/generated report files require controlled storage, expiry/cleanup and authorized download access.
- SAP write-back requires authenticated and specifically authorized server-side execution.
- Validate outbound payloads against strict schemas and approved business states before transmission.
- Use idempotency/deduplication controls to prevent accidental duplicate SAP writes.
- SAP credentials/tokens/certificates must remain server-side and follow the existing secrets policy.
- Record auditable write-back attempts, actor/system identity, target action, timestamps and outcome without logging sensitive credentials.
- Return safe user-facing failures while retaining detailed server-side diagnostic logs.
- Forecast/ML output alone must never authorize an SAP write.
