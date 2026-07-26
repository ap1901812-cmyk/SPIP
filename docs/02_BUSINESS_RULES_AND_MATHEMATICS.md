# 02 — Business Rules and Mathematics
Specification
Supply Planning Intelligence Platform (SPIP)
Document Type: Business Rules & Mathematical Specification
Product: Supply Planning Intelligence Platform
Status: Enterprise Rebuild Specification
Primary Purpose: Define the authoritative business rules, calculations, statistical methods, decision
rules, assumptions, and validation requirements used by SPIP .
### 1. Purpose
This document defines the business and mathematical logic used by the Supply Planning Intelligence
Platform.
It exists to prevent critical planning calculations from becoming undocumented implementation details
hidden inside source code.
All calculations affecting inventory, material status, demand, safety stock, allocation, or planning
recommendations must be traceable to an approved rule in this document.
The implementation must not change these rules merely for programming convenience.
### 2. Design Principles
SPIP shall follow these principles for business calculations.
### BR-P01 — Mathematical Correctness
Every production calculation must have a documented formula, defined variables, units, assumptions,
edge-case behavior , and automated tests.
### BR-P02 — Business Meaning Before Formula
A mathematically valid formula shall not be used unless it represents the intended business process.
### BR-P03 — Deterministic Logic vs Forecasting
Inventory and allocation calculations shall remain separate from predictive forecasting.
Forecasting estimates future demand.

The deterministic planning engine uses the forecast together with inventory, purchase orders, safety
stock, lead time, allocations, and business rules to calculate planning requirements.
### BR-P04 — No Silent Assumptions
Missing values must not automatically become zero unless the relevant business rule explicitly defines
zero as the correct interpretation.
### BR-P05 — Unit Consistency
Calculations may only combine quantities expressed in compatible units.
Required unit conversion shall occur before the calculation.
### BR-P06 — Explainability
Important calculated outputs must be traceable to their input values and calculation version.
### BR-P07 — Configurable Parameters
Business thresholds expected to change shall be configuration rather than hardcoded application
constants.
### 3. Core Planning Flow
The conceptual SPIP planning flow is:
Enterprise/SAP Data
        ↓
Data Validation
        ↓
Material + Inventory + Consumption + PO Data
        ↓
Consumption Statistics
        ↓
Demand Forecast
        ↓
Safety Stock
        ↓
Inventory Position
        ↓
Net Material Requirement
        ↓
Material Criticality
        ↓
Planner Review
        ↓
Vendor Allocation

↓
Approval / Communication
        ↓
Audit & Reporting
Forecasting shall provide an input to planning rather than directly executing procurement.
### 4. Authoritative Input Data
Planning calculations may require the following logical inputs:
Material ID
Material description
Material type
Unit of measure
Historical consumption
Current inventory
Open purchase orders
Supplier lead time
Safety-stock parameters
Existing allocations
Planning horizon
Production requirements where applicable
BOM requirements where applicable
Material configuration
Vendor information
The authoritative system for each input shall be defined in the technical and integration specifications.
### 5. Data Validation Before Calculation
No critical calculation shall run blindly on unvalidated data.
At minimum, validation shall consider:
missing material identifiers;
invalid dates;
duplicate observations;
negative quantities where not permitted;
incompatible units;
missing lead time;
impossible inventory values;
malformed numeric values;
stale source data;
insufficient forecasting history.
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
•
•
•
•

Invalid records shall be rejected, quarantined, or explicitly flagged according to the applicable data-
quality rule.
They shall not silently distort planning calculations.
### 6. Consumption
For a material , let:
represent validated consumption during time period .
The system shall preserve the distinction between:
zero consumption;
missing consumption;
unavailable data.
A missing observation shall not automatically be interpreted as zero consumption.
### 7. Rolling Consumption Window
The reference application uses recent rolling consumption statistics, including a seven-day window.
For a seven-period window ending at time :
From the valid observations in this window, the system may calculate:
minimum;
maximum;
mean;
standard deviation.
The exact window shall be configurable where business requirements justify it.
The seven-day window from the reference application shall therefore be treated as a baseline business
configuration, not an immutable mathematical law.
### 8. Average Consumption
For  valid observations:
m
C
t
t
•
•
•
t
W =t {C ,...,C}t−6 t
•
•
•
•
n

where:
 = consumption observation;
 = number of valid observations;
 = arithmetic mean consumption.
Example:
Consumption:
100, 110, 90, 120, 100
Average = 104
The mean provides a central estimate of historical consumption but does not independently represent
future demand.
### 9. Minimum and Maximum Consumption
For observations :
These statistics describe observed historical extremes.
They shall not automatically be interpreted as forecast boundaries.
### 10. Standard Deviation
Standard deviation represents the variability of consumption around its mean.
The implementation shall explicitly define whether sample or population standard deviation is being
calculated.
For a population:
Higher standard deviation indicates more variable historical consumption.
=Cˉ C
n
i=1
∑
n
i
• C
i
• n
• Cˉ
C,...,C
1 n
C =min min(C,...,C)1 n
C =max max(C,...,C)1 n
σ= (C − )n
i=1
∑
n
i Cˉ2

The chosen statistical definition must be identical across backend calculations, reports, tests, and
documentation.
### 11. Reference-System Consumption Bands
The reference project uses derived values conceptually equivalent to:
and:
These values may be useful as consumption-band indicators.
However , they shall not automatically be accepted as statistically authoritative planning
thresholds merely because they exist in the reference code.
Before production implementation they must be mapped to a documented business purpose.
The enterprise implementation shall classify them as:
Legacy business rules requiring validation.
If retained, their exact role in criticality or consumption classification shall be documented and tested.
### 12. Safety Stock
The reference implementation uses a safety-stock concept based on:
where:
 = safety stock;
 = service-level factor;
 = standard deviation of demand per period;
 = lead time expressed in compatible periods.
This formula assumes demand variability while lead time is treated as sufficiently stable.
### 13. Service Level
The -value represents the target cycle service level under the assumptions of the selected safety-stock
model.
C −max σ
+Cˉ σ
SS=Zσ
d LT
• SS
• Z
• σ
d
• LT
Z

The reference implementation has used approximately:
corresponding approximately to a 95% one-sided normal service level.
The enterprise system shall not permanently hardcode 1.65.
Target service levels shall be approved business configuration and may eventually vary by material class
or business criticality.
### 14. Variable Lead-Time Safety Stock
Where both demand and supplier lead time vary materially, the simpler safety-stock formula may be
insufficient.
A more general candidate formulation is:
where:
 = average lead time;
 = demand standard deviation;
 = average demand per period;
 = lead-time standard deviation.
This formula shall only be used where its assumptions match the available business data.
The enterprise implementation shall select the safety-stock method according to validated data
availability and approved business requirements.
### 15. Safety-Stock Edge Cases
The implementation must explicitly handle:
missing lead time;
zero lead time;
negative lead time;
insufficient demand history;
zero demand variability;
extreme outliers;
incompatible time units;
missing service-level configuration.
No NaN, infinity, negative safety stock, or unexplained fallback value shall be silently exposed as a valid
planning result.
Z=1.65
SS=Z LTσ + σ
d2 Dˉ2 LT2
• LT
• σ
d
• Dˉ
• σ
LT
•
•
•
•
•
•
•
•

### 16. Reorder Point
Where reorder-point logic is required:
For approximately constant daily demand:
where:
 = reorder point;
 = average demand per day;
 = lead time in days;
 = safety stock.
Reorder point answers:
At what inventory position should replenishment action be triggered?
It does not by itself determine the optimal purchase quantity.
### 17. Inventory Position
Planning must distinguish physical stock from effective inventory position.
A conceptual inventory position may be:
Additional components may be included according to approved enterprise business definitions.
The exact treatment of:
quality stock;
blocked stock;
in-transit stock;
open PO;
reservations;
allocations
must be documented before implementation.
ROP=D +LT SS
ROP=( ×Dˉ LT)+SS
• ROP
• Dˉ
• LT
• SS
IP=OnHand+ConfirmedIncoming−CommittedQuantity
•
•
•
•
•
•

### 18. Gross Requirement
Gross requirement represents the quantity required before considering available inventory and
incoming supply.
Where SPIP receives production requirements through MRP/BOM logic, gross requirement may be
derived from:
subject to approved BOM, yield, scrap, conversion, and unit rules.
### 19. Net Requirement
A baseline planning relationship is:
subject to the organization's exact business definition.
The result shall normally be bounded:
unless negative requirements have an explicitly defined business meaning.
The system shall not recommend procurement merely because the mathematical expression produced
a negative or invalid intermediate value.
### 20. Forecast-Based Requirement
Where future demand forecasting is used:
A conceptual shortage quantity may then be:
The exact production formula shall be finalized after validating how the reference project treats stock,
open POs, allocations, and safety stock.
GR =m ProductionRequirement ×
p
∑ p BOMQuantity
p,m
NR=GR+SS−AvailableInventory−EligibleOpenSupply
NR =final max(0,NR)
ProjectedRequirement=ForecastDemand+RequiredBuffer
Shortage=max(0,ProjectedRequirement−ProjectedAvailableSupply)

### 21. Demand Forecasting Boundary
The forecasting engine answers:
What future demand is expected?
The deterministic planning engine answers:
Given forecast demand, stock, incoming supply, safety stock and business rules, what
action should be considered?
These responsibilities must remain separate.
SPIP shall never define:
ML forecast
     ↓
Automatic purchase order
without an independently approved workflow.
### 22. Forecasting Baseline
The reference project uses a recent-history moving-average/trend-based forecasting technique.
This shall remain available as:
a baseline for model comparison;
a fallback method where appropriate.
It shall not automatically remain the primary production forecasting method.
Detailed model selection is defined in FORECASTING.md.
### 23. Forecast Horizon
The reference application generates approximately a twelve-day forward forecast.
The enterprise platform shall treat the forecast horizon as a business configuration.
For the initial rebuild:
12 days shall remain the reference baseline unless business validation establishes a different
horizon.
•
•

Forecast evaluation must match the intended planning horizon.
### 24. Forecast Accuracy
Forecast models shall be evaluated against historical observations through backtesting rather than
selected because they appear sophisticated.
Candidate metrics include:
MAE;
RMSE;
WMAPE;
forecast bias.
The final model-evaluation policy belongs to FORECASTING.md.
MAPE shall be used cautiously where actual consumption can be zero or near zero.
### 25. Forecast Fallback
Forecasting shall support graceful degradation.
Conceptually:
Selected validated model
        ↓
Unable to produce acceptable forecast?
        ↓
Approved secondary/baseline model
        ↓
Still unavailable?
        ↓
Simple deterministic fallback
        ↓
Flag reduced confidence
A fallback must be visible and auditable.
### 26. Forecast Uncertainty
Forecasts shall not be represented as guaranteed future demand.
•
•
•
•

Where supported, the system should provide:
point forecast;
uncertainty interval;
historical error;
model/fallback status.
Example:
Forecast: 1,250 kg
Expected range:
1,100–1,400 kg
Model status:
Validated
Historical WMAPE:
7.8%
### 27. Material Criticality
Material criticality shall represent planning urgency.
The reference application uses status concepts comparable to:
Critical;
Warning;
OK/Healthy.
The enterprise version shall preserve this capability while formally documenting the thresholds.
A conceptual framework is:
Projected supply insufficient
for protected planning horizon
        ↓
CRITICAL
Supply approaching protected threshold
        ↓
WARNING
Adequate projected coverage
        ↓
HEALTHY
•
•
•
•
•
•
•

The exact production rule must be based on validated inventory position, demand/forecast, safety
stock, lead time, and incoming supply.
### 28. Criticality Explainability
A status shall never appear without a reason.
For example:
Status: CRITICAL
Reason:
Projected inventory falls below
safety stock within supplier lead time.
Current Stock: 2,100 kg
Open Supply: 500 kg
Forecast Demand: 2,000 kg
Safety Stock: 900 kg
This allows planners to validate the system's reasoning.
### 29. Allocation
Allocation represents an approved quantity assigned to a vendor or applicable supply source.
The system must validate allocation before persistence.
At minimum:
where available allocatable quantity is calculated according to the approved business rule.
### 30. Existing Allocation Calculation
When creating a new allocation:
subject to status and cancellation rules.
NewAllocation≤AvailableAllocatableQuantity
Available=Requirement−ExistingActiveAllocations

When editing an existing allocation, the allocation currently being edited must not be counted against
itself.
Therefore:
and:
This prevents the system from incorrectly treating the existing quantity as a competing allocation
during an edit.
### 31. Allocation Example
Suppose:
Requirement = 1,000 kg
Vendor A allocation = 400 kg
Vendor B allocation = 300 kg
Remaining quantity:
Vendor C may therefore receive at most 300 kg.
Now suppose Vendor A's existing allocation is being edited.
The system must exclude Vendor A's current 400 kg while calculating how much Vendor A may now be
assigned.
Other allocations:
Therefore Vendor A may be edited up to:
Without this exclusion, the system could incorrectly restrict the edit.
OtherAllocations=TotalActiveAllocations−CurrentAllocation
EditableAvailable=Requirement−OtherAllocations
1000−400−300=300
1000−300=700

### 32. Allocation Concurrency
Frontend validation alone is insufficient.
Two planners may attempt allocation simultaneously.
Example:
Available = 500 kg
Planner A sees 500
Planner B sees 500
A allocates 400
B allocates 400
Without database-level transaction/concurrency protection:
Total allocation = 800 kg
which violates the requirement.
Allocation validation must therefore be enforced atomically at the backend/database transaction level.
### 33. Allocation Quantity Rules
Allocation quantity shall:
be numeric;
use an approved unit;
normally be greater than zero;
not exceed authorized availability;
respect material/vendor eligibility;
respect applicable status;
respect user permissions.
Rounding and decimal precision shall be defined by unit-of-measure rules.
### 34. Allocation Status
The final workflow may include statuses such as:
Draft;
•
•
•
•
•
•
•
•

Pending Approval;
Approved;
Communicated;
Cancelled.
Only statuses approved in the workflow specification shall affect planning totals.
Cancelled allocations, for example, should normally not consume available allocation quantity.
### 35. Purchase Order Treatment
Open purchase orders shall not automatically be treated as guaranteed available stock.
PO quantities may require classification such as:
confirmed;
partially received;
delayed;
cancelled;
closed.
Only supply considered eligible according to the approved rule shall contribute to projected availability.
### 36. Lead Time
Lead time shall use a consistent unit.
If demand is daily and lead time is provided in weeks, the value must be converted before formulas
combining the two are evaluated.
Lead time may eventually distinguish:
contractual lead time;
historical actual lead time;
expected lead time.
The forecasting/planning system must document which value is used.
### 37. EOQ
If Economic Order Quantity is included in future replenishment recommendations:
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
EOQ=
H
2DS

where:
 = annual demand;
 = ordering cost per order;
 = annual holding cost per unit.
EOQ shall not be implemented merely because it is a standard inventory formula.
It requires valid ordering-cost and holding-cost inputs and business validation.
Therefore EOQ is classified as:
Optional / future planning capability unless required by the validated reference workflow.
### 38. Rounding
Intermediate calculations should retain sufficient numeric precision.
Rounding shall normally occur only at defined business boundaries such as:
display;
purchasable unit;
packaging multiple;
approved order quantity.
Rounding rules shall not vary silently between frontend and backend.
### 39. Missing Data
Missing data shall have explicit behavior .
Examples:
Missing consumption
≠ automatically zero consumption
Missing lead time
≠ automatically zero-day lead time
Missing PO
≠ automatically zero unless source completeness is known
Missing forecast
≠ automatically zero demand
• D
• S
• H
•
•
•
•

Critical missing data shall generate a data-quality condition where appropriate.
### 40. Outliers
Extreme historical observations can substantially alter:
mean;
standard deviation;
safety stock;
forecast.
SPIP shall not silently delete outliers.
Outlier handling must distinguish between:
genuine unusual demand;
data-entry error;
duplicate data;
system/integration error;
legitimate business event.
Any automated treatment must be documented in FORECASTING.md.
### 41. Negative Values
Negative values shall be accepted only where their business meaning is explicitly defined.
Examples might include:
reversals;
returns;
corrections.
A negative quantity shall never be accepted merely because the database column supports negative
numbers.
### 42. Time Zones and Business Dates
Business calculations based on dates shall use an explicitly defined business timezone and calendar .
Daily consumption aggregation must not vary depending on the timezone of the application server .
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

### 43. Calculation Versioning
Critical calculation logic shall be versioned.
Example:
Safety Stock Method:
SS-DEMAND-V1
Criticality Rule:
CRIT-V2
Net Requirement:
NR-V1
Where practical, calculated records shall retain enough metadata to identify the calculation/rule version
used.
This is essential when formulas evolve later .
### 44. Calculation Auditability
For important recommendations, SPIP should be capable of recording or reconstructing:
input values;
formula/rule version;
calculated result;
calculation timestamp;
source-data version/time;
relevant configuration.
This allows future investigation of:
Why did SPIP recommend this quantity on this date?
### 45. Deterministic Reproducibility
Given:
identical validated inputs;
identical configuration;
identical business-rule version;
deterministic calculations must produce identical outputs.
•
•
•
•
•
•
•
•
•

Unexpected differences shall be treated as defects.
ML forecasting is separately governed because model state/version also affects its output.
### 46. Backend as Calculation Authority
The frontend may display preview calculations for usability.
However:
The backend is the authoritative source for business calculations.
A frontend preview shall never override backend validation.
This specifically prevents UI/backend inconsistencies such as those identified in the reference project.
### 47. Calculation Testing
Every critical formula shall have automated tests covering:
normal case;
zero values;
boundary values;
missing values;
invalid values;
large values;
rounding;
unit conversion;
historical regression cases.
Example:
Given:
Demand SD = 20 units/day
Lead Time = 9 days
Z = 1.65
Expected:
SS = 1.65 × 20 × √9
   = 99 units
The automated test must produce the approved result within defined numeric tolerance.
•
•
•
•
•
•
•
•
•

### 48. Reference-System Logic Classification
Logic discovered in the original RMPM project shall be classified before being copied.
PRESERVE
Business rule is valid and implementation is correct.
CORRECT
Business concept is valid but implementation contains a defect.
REFINE
Concept is useful but requires clearer enterprise rules/configuration.
REPLACE
Existing approach is inadequate and an approved replacement exists.
VALIDATE
Insufficient business evidence exists to accept or reject the rule.
This classification prevents accidental preservation of bugs.
### 49. Initial Classification of Known Reference
Logic
Existing Logic Enterprise Treatment
Rolling consumption statistics REFINE
7-day rolling window VALIDATE / configurable baseline
Average consumption PRESERVE
Min/max consumption PRESERVE
Standard deviation PRESERVE with explicit statistical definition
Max − SD VALIDATE
Average + SD VALIDATE
Safety stock concept PRESERVE
Fixed Z ≈ 1.65 REFINE to configuration
Simple moving-average/trend forecastPRESERVE as baseline/fallback

Existing Logic Enterprise Treatment
12-day forecast horizon VALIDATE / configurable baseline
Critical/Warning/OK concept PRESERVE
Existing criticality thresholds VALIDATE
Vendor allocation PRESERVE
Exclude current allocation during editPRESERVE
Frontend-only allocation validationREPLACE
ML forecasting NEW enterprise capability
Forecast fallback NEW enterprise capability
Calculation versioning NEW enterprise capability
### 50. Source-of-Truth Rule
For implementation purposes:
This document is authoritative for approved business and mathematical behavior.
However:
FORECASTING.md is authoritative for forecasting-model implementation;
SECURITY.md is authoritative for security controls;
DATABASE.md is authoritative for persistence design;
API.md is authoritative for interface contracts.
If source code conflicts with an approved business rule in this document, the conflict must be
investigated rather than silently treating existing code as correct.
### 51. Rules Requiring Validation Before Production
The following items require confirmation against the reference implementation, real business process,
or domain-owner requirements before being frozen for production:
exact seven-day consumption-window purpose;
exact purpose of Max − SD;
exact purpose of Average + SD;
exact critical/warning/healthy thresholds;
exact safety-stock service-level policy;
whether supplier lead-time variability is available;
exact treatment of open purchase orders;
exact definition of available stock;
•
•
•
•
1.
2.
3.
4.
5.
6.
7.
8.

exact treatment of existing allocations;
exact forecast horizon;
exact production/BOM relationship where applicable;
rounding and unit-conversion rules.
Claude shall not invent these values during implementation.
Where an unresolved item affects a feature ticket, implementation shall stop at that decision boundary
or use an explicitly approved temporary configuration.
### 52. Implementation Rule for AI Development
When implementing a ticket involving business calculations, the coding agent shall:
read the relevant section of this document;
read the feature ticket;
inspect existing implementation where applicable;
identify the approved formula/rule;
implement it in the authoritative backend domain/service layer;
add unit tests;
add boundary/edge-case tests;
ensure frontend displays consistent values;
document any unresolved assumption;
never modify the formula merely to make a failing test pass.
### 53. Final Business Principle
SPIP shall not attempt to make supply-chain decisions appear more certain than the available data
permits.
The platform shall combine:
validated data + mathematically correct deterministic rules + validated forecasting + business
configuration + human oversight
to produce reliable and explainable supply-planning intelligence.
End of Business Rules and Mathematics Specification
9.
10.
11.
12.
1.
2.
3.
4.
5.
6.
7.
8.
9.
10.
