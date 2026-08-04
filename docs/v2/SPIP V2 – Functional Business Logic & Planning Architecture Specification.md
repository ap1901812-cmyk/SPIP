

# **SPIP V2 – Functional Business Logic & Planning Architecture Specification**

# 1. Introduction

## 1.1 Purpose of SPIP

SPIP (Supply Planning & Inventory Platform) is an enterprise decision support system designed to help planners make better decisions regarding inventory, procurement, vendor allocation, and production planning.

The current version of SPIP mainly focuses on forecasting, inventory planning, BOM explosion, and report generation. However, after studying the RMPM business logic and understanding the real industrial workflow, the system is being redesigned to support complete material planning rather than only forecasting.

The objective is to build a platform that can answer questions like:

* Which materials will become critical?
* Which Finished Goods cannot be produced?
* How much material should be procured?
* Which vendor should receive the order?
* When should procurement happen?
* Which plant is at risk?
* What action should the planner take next?

Instead of only displaying reports, SPIP should become a system that helps planners make informed business decisions.

# 1.2 Business Objective

The primary objective of SPIP V2 is to convert raw business data into meaningful planning recommendations.

Instead of asking the planner to manually analyze hundreds of records from SAP or Excel files, the system will automatically process the available information and provide recommendations.

The system should:

* Collect data from different sources.
* Validate uploaded data.
* Calculate inventory and planning parameters.
* Forecast future demand.
* Estimate Raw Material and Packaging Material requirements.
* Generate procurement recommendations.
* Suggest vendor allocations.
* Help planners understand production readiness.
* Generate business reports for decision making.

The planner will always remain the final decision maker. SPIP will recommend actions but will never automatically execute business decisions.

# 1.3 Current Problem

Today, planners generally work with multiple Excel sheets, SAP reports, manual calculations, and different planning systems.

Some common challenges are:

* Data is available in multiple locations.
* Manual calculations consume a lot of time.
* Inventory shortages are identified very late.
* Vendor allocation is mostly reactive.
* Different planners may make different decisions using the same data.
* There is no single platform that combines forecasting, planning, procurement, and reporting.

SPIP aims to solve these problems by bringing everything into one unified planning platform.

# 1.4 Scope of SPIP V2

SPIP V2 will cover the complete material planning workflow.

The system will include:

* Data Ingestion
* Consumption Analysis
* Inventory Planning
* Forecasting
* Safety Stock Calculation
* Trigger Calculation
* Raw Material Planning
* Packaging Material Planning
* Dependency Analysis
* Procurement Recommendations
* Vendor Allocation
* Production Readiness
* Reports & Dashboards

The system will support both manual uploads and SAP integration.

# 2. Planning Philosophy

## 2.1 Existing Planning Approach

The existing SPIP workflow is relatively simple.

```text
Forecast

↓

Planning

↓

Reports
```

Although this approach works, it only considers forecasting as the main input.

Real industries use many more business parameters while making procurement decisions.

## 2.2 New Planning Philosophy

The new SPIP follows a much broader planning approach.

Planning should not depend only on forecasting.

Instead, planning should consider:

* Current Inventory
* Purchase Orders
* Gate Entries
* Consumption
* Safety Stock 1 & 2
* Lead Time 1 & 2
* Forecast
* IBP Requirements
* Monthly Requirement
* Vendor Capacity
* Vehicle Capacity
* Plant Storage Capacity

All these inputs together help generate better planning recommendations.

The overall workflow becomes:

```text
Data Sources

↓

Data Ingestion

↓

Validation

↓

Planning Intelligence

↓

Procurement Recommendation

↓

Planner Approval

↓

Vendor Communication

↓

Reports & Dashboard
```

This philosophy changes SPIP from a reporting application into a complete planning support platform.

# 2.3 Planner-Centric System

One important principle followed in SPIP V2 is that the system will **recommend** decisions but **not automatically execute** them.

For example:

The system may recommend:

* Purchase 25 Tons of RM-1001.
* Allocate Vendor A for this order.
* Dispatch material on 12 August.

However, the planner will always have the option to:

* Accept the recommendation.
* Modify the quantity.
* Change the vendor.
* Delay the procurement.
* Reject the recommendation.

This ensures that business knowledge and human judgement remain part of the planning process.

# 3. Data Sources

The quality of planning depends completely on the quality of input data.

SPIP accepts information from three major sources.

## 3.1 SAP Data

SAP provides operational business data.

Examples include:

* Purchase Orders
* Gate Entry
* Current Inventory
* Consumption
* Material Master
* Vendor Master (if available)
* Plant Information (if available)

SAP data is considered highly reliable because it reflects actual business transactions.

## 3.2 IBP Data

IBP (Integrated Business Planning) provides planning-related information.

Examples include:

* Daily Requirement
* Planning Demand
* Production Planning Information

IBP data helps the planning engine understand future business requirements.

## 3.3 Manual Data

Some business information may not exist inside SAP.

Examples include:

* Monthly Requirement
* Lead Time 1
* Lead Time 2
* Vendor Capacity
* Vehicle Capacity
* Plant Storage Capacity
* RM Totality Mapping
* PM Manual Adjustments

Such information can be uploaded manually using Excel or CSV files.

# 4. Data Ingestion Engine

## 4.1 Purpose

The Data Ingestion Engine is the first component of SPIP.

Its responsibility is to collect data from different sources and prepare it for planning.

No planning calculations begin until data has been successfully ingested and validated.

## 4.2 Supported File Formats

SPIP supports:

* Excel (.xlsx)
* CSV (.csv)

Multiple files can be uploaded together.

For example:

```
PurchaseOrders.xlsx

Consumption.xlsx

Inventory.xlsx

IBP.xlsx

VehicleCapacity.xlsx

VendorCapacity.xlsx
```

The system automatically identifies each file based on its structure and required columns.

The user does not need to manually specify the file type.

## 4.3 Data Validation

Before storing any information, SPIP validates the uploaded files.

The system checks:

* Required columns
* Missing values
* Duplicate records
* Invalid material codes
* Invalid plant codes
* Invalid vendor codes

If errors are found, the planner receives a clear message explaining the problem.

Example:

```
Vendor Capacity file missing.

Procurement recommendations cannot be generated.
```

Instead of silently ignoring missing data, SPIP always informs the user about incomplete information.

## 4.4 Automatic Master Creation

One important improvement in SPIP V2 is automatic master generation.

If a separate Plant Master or Vendor Master is not available, the system attempts to derive this information from uploaded transactional data.

For example:

If Purchase Orders contain:

```
Vendor : V001

Plant : 1000
```

SPIP automatically creates internal Vendor and Plant records.

This reduces unnecessary manual uploads and simplifies the data ingestion process.

## 4.5 Planning Trigger

Whenever new data is uploaded successfully, SPIP automatically refreshes the planning calculations.

The following modules are recalculated:

* Consumption Analysis
* Inventory Planning
* Forecasting
* Safety Stock
* Trigger Levels (1 & 2)
* Material Criticality
* Procurement Recommendations
* Production Readiness
* Reports

A manual **"Generate Planning"** button will also be available so planners can refresh calculations whenever required.

# 4.6 Output of the Data Ingestion Engine

Once data ingestion is completed successfully, the system prepares clean and validated business data for all downstream planning modules.

This validated data becomes the foundation for every calculation performed in SPIP.

No planning recommendation is generated without first passing through the Data Ingestion Engine.

* **Consumption Intelligence Engine**
* **Inventory Intelligence Engine**
* **Safety Stock & Trigger Engine**
* **Lead Time 1 & Lead Time 2 Logic (from RMPM)**
* **Material Criticality Logic**

# **SPIP V2 – Functional Business Logic & Planning Architecture Specification**

# **5. Consumption Intelligence Engine**

## **5.1 Purpose**

The Consumption Intelligence Engine is the first analytical module of SPIP after data ingestion.

Its primary purpose is to understand **how materials are actually being consumed inside each plant**. Instead of simply storing historical consumption records, the engine converts them into meaningful planning information that can be used for forecasting, inventory planning, procurement recommendations, and material criticality analysis.

Consumption is one of the most important planning inputs because it reflects the actual usage of materials in production.

## **5.2 Why Consumption Analysis is Important**

Procurement decisions should not be based only on the current stock available at the plant. They must also consider how quickly that stock is being consumed.

For example:

```
RM-1001

Current Stock : 300 Tons

Daily Consumption : 10 Tons
```

Although the current stock appears to be sufficient, the available inventory will last for only 30 days.

Now consider another material:

```
RM-1002

Current Stock : 300 Tons

Daily Consumption : 2 Tons
```

Even though both materials have the same stock quantity, RM-1002 can support production for a much longer period.

This simple comparison shows why consumption analysis is necessary before making procurement decisions.

## **5.3 Input Data**

The Consumption Intelligence Engine primarily uses the following inputs:

### SAP Data

* Historical Consumption
* Material Code
* Plant
* Posting Date
* Quantity Consumed

### Additional Inputs

* Monthly Requirement (Manual)
* IBP Daily Requirement
* Production Planning Data

If one source is unavailable, the system automatically uses the next available source while informing the planner about the missing data.

## **5.4 Consumption Calculation**

The engine calculates several planning parameters from historical consumption.

These include:

* Total Consumption
* Daily Average Consumption
* Weekly Average Consumption
* Monthly Average Consumption
* Consumption Trend
* Material-wise Consumption
* Plant-wise Consumption

These values become the foundation for inventory planning and forecasting.

## **5.5 Consumption Classification**

Instead of treating every material equally, SPIP classifies materials based on their usage patterns.

Typical classifications include:

* Stable Consumption
* Increasing Consumption
* Decreasing Consumption
* Seasonal Consumption
* Irregular Consumption

This classification helps the forecasting engine select the most suitable forecasting model.

For example:

| Consumption Pattern | Preferred Forecasting Approach |
| ------------------- | ------------------------------ |
| Stable              | Moving Average                 |
| Increasing          | Exponential Smoothing          |
| Seasonal            | Seasonal Forecasting           |
| Highly Variable     | Manual Review Required         |

## **5.6 Output of the Consumption Engine**

The Consumption Intelligence Engine provides:

* Daily Consumption
* Weekly Consumption
* Monthly Consumption
* Consumption Trend
* Material Consumption Classification
* Planning Inputs for Forecasting
* Planning Inputs for Inventory Intelligence

This information is forwarded to the next planning module.

# **6. Inventory Intelligence Engine**

## **6.1 Purpose**

The Inventory Intelligence Engine determines whether the current inventory is sufficient to support future production.

Instead of simply displaying stock quantities, it evaluates inventory from a planning perspective.

The objective is to answer questions such as:

* Is enough inventory available?
* How long will the inventory last?
* Which materials are likely to become critical?
* Which materials require procurement?

## **6.2 Input Data**

The Inventory Intelligence Engine uses:

### SAP Data

* Current Stock
* Purchase Orders
* Gate Entries
* Material Master

### Planning Inputs

* Daily Consumption
* Monthly Requirement
* Forecasted Demand

## **6.3 Inventory Availability**

The first calculation performed is the Planning Available Inventory.

The system combines:

```
Current Stock

+

Incoming Purchase Orders

+

Gate Entries

=

Planning Available Inventory
```

This value represents the inventory that is expected to be available for planning purposes.

## **6.4 Days of Inventory**

The next calculation estimates how many days the available inventory can support production.

```
Days of Inventory

=

Planning Available Inventory

/

Daily Consumption
```

Example:

```
Planning Available Inventory

600 Tons

Daily Consumption

20 Tons

Days of Inventory

30 Days
```

This is one of the most useful planning indicators because planners can immediately estimate when procurement will become necessary.

## **6.5 Inventory Health**

Based on inventory calculations, each material is assigned an inventory health status.

The available statuses are:

🟢 Healthy

Enough inventory is available.

🟡 Low Stock

Inventory is reducing and should be monitored.

🟠 Reorder Required

Procurement should begin soon.

🔴 Critical

Immediate procurement is required to avoid production disruption.

These statuses are displayed throughout the dashboard and planning screens.

## **6.6 Inventory Intelligence Output**

The Inventory Intelligence Engine provides:

* Planning Available Inventory
* Days of Inventory
* Inventory Health
* Material Criticality Inputs
* Procurement Planning Inputs

These outputs become direct inputs for the Statistical Planning Engine.

# 7. Statistical Planning Engine (RMPM Methodology)

## 7.1 Purpose

The Statistical Planning Engine is the planning foundation of SPIP V2. It converts inventory and consumption information into critical planning parameters that determine when procurement should be initiated. 

Instead of using generic statistical formulas, SPIP V2 adopts the **RMPM statistical planning methodology**. This approach recognizes that procurement dynamics change depending on whether a supply cycle is being initiated or is already in a regular replenishment phase.

The primary outputs of this module are:

*   Lead Time (LT-1 & LT-2)
*   Safety Stock (SS-1 & SS-2)
*   Reorder Triggers (Trigger-1 & Trigger-2)

## 7.2 Lead Time Philosophy

SPIP V2 does not calculate a single Lead Time. Instead, every material maintains two independent Lead Time states to reflect real-world procurement conditions.

### 7.2.1 Lead Time 1 (LT-1): Initial Procurement Lead Time

Lead Time 1 represents the time required when procurement is initiated without an existing replenishment cycle. This is used when the vendor is not yet supplying the material continuously. 

LT-1 represents the complete end-to-end procurement duration, including:

*   **Vendor Planning:** The time the vendor needs to schedule production.
*   **Raw Material Sourcing:** Time for the vendor to procure their own materials.
*   **Manufacturing & Processing:** The actual production time at the vendor's facility.
*   **Dispatch & Transportation:** Moving the finished material to the plant.
*   **Plant Receiving:** Internal processes for unloading and quality checks.

Because the vendor is not maintaining ready inventory for the plant, **LT-1 is normally longer**.

### 7.2.2 Lead Time 2 (LT-2): Regular Supply Lead Time

Lead Time 2 is used once a continuous supply relationship is established. As the planner initiates regular orders, the vendor begins to understand the consumption pattern and maintains a ready inventory buffer.

In this state, many initial activities are eliminated, leaving only operational steps:

*   **Dispatch:** Immediate release of ready stock.
*   **Transportation:** Moving material to the plant.
*   **Plant Receiving:** Standard internal receiving processes.

Consequently, **LT-2 is significantly shorter than LT-1**. This dual-lead-time approach allows the system to be more efficient during regular operations while remaining safe during initial procurement.

## 7.3 Safety Stock Buffers

Safety Stock in SPIP V2 is not defined by a single equation but by two planning safety buffers that correspond to the Lead Time states.

### 7.3.1 Safety Stock 1 (SS-1)

Calculated based on **LT-1**, this buffer is used for initial procurement. It is designed to protect the plant against uncertainty before a continuous and stable supply is established. SS-1 is generally higher to provide maximum protection during the longer initial lead time.

### 7.3.2 Safety Stock 2 (SS-2)

Calculated based on **LT-2**, this buffer is used after continuous replenishment starts. Because the supply chain is now more stable and the lead time is shorter, the required safety buffer is usually lower. This prevents unnecessary inventory buildup while still maintaining a safe operational cushion.

## 7.4 Reorder Trigger Logic

SPIP V2 maintains two distinct procurement triggers to guide the planner's actions.

### 7.4.1 Trigger 1 (Initial Cycle)

Based on **LT-1 planning**, Trigger 1 represents the inventory level at which the very first procurement cycle should begin. Crossing this level signals the system to start **proactive procurement** to account for the longer initial lead time.

### 7.4.2 Trigger 2 (Regular Replenishment)

Based on **LT-2 planning**, Trigger 2 represents the inventory level maintained during regular replenishment. It supports continuous supply planning, ensuring that new orders are placed just in time to replenish the stock used during the shorter LT-2 period.

## 7.5 Planning States & Integration

Every material in SPIP V2 simultaneously maintains these six planning states:
*   **LT-1 & LT-2**
*   **SS-1 & SS-2**
*   **Trigger-1 & Trigger-2**

These values are continuously maintained by the Statistical Planning Engine. All downstream modules in SPIP V2 consume these outputs directly rather than implementing their own independent planning logic. This ensures total consistency across:

*   Forecasting & Requirement Resolution
*   RM & PM Planning Engines
*   Procurement Recommendation & Allocation Engines

## 7.6 Operational Business Constraints

After the statistical planning stage, the engine considers real-world operational constraints to refine procurement plans:

*   **Vendor & Material Capacity:** Maximum quantity a supplier can provide.
*   **Vehicle Capacity:** Optimization based on transport sizes.
*   **Plant Storage Capacity:** Physical limits on how much material can be stored.
*   **Supply Frequency & PR to PO Time:** Administrative and logistical timings.

By adopting the RMPM methodology, SPIP V2 ensures that its recommendations are grounded in industrial reality rather than just theoretical statistics.

# **8. Forecasting Engine**

## **8.1 Purpose**

The purpose of the Forecasting Engine is to estimate future material demand based on historical consumption patterns.

Procurement decisions should not rely only on today's inventory because procurement requires time. By the time inventory becomes critical, it may already be too late to receive new material.

Forecasting allows the planner to anticipate future demand and initiate procurement before shortages occur.

Instead of reacting to shortages, SPIP aims to predict them.

## **8.2 Why Forecasting is Required**

Consider the following example:

```text
Today's Stock : 250 Tons

Daily Consumption : 10 Tons

Lead Time : 15 Days
```

Although 250 tons appears sufficient today, after 15 days only 100 tons will remain.

If procurement starts after inventory becomes low, the plant may experience a stockout before the new material arrives.

Forecasting allows the system to identify such situations in advance and recommend procurement before production is affected.

## **8.3 Input Data**

The Forecasting Engine uses the following inputs:

* Historical Material Consumption
* Daily Consumption Trend
* Monthly Requirement
* IBP Daily Requirement (if available)
* Planning Horizon (15 Days)

These inputs are collected from the Consumption Intelligence Engine and the Data Ingestion Engine.

## **8.4 Forecasting Models**

SPIP supports multiple forecasting models.

Initially, the following models are available:

* Moving Average
* Exponential Smoothing
* Holt-Winters

Although multiple models exist, the system does not blindly use all of them for production planning.

Instead, it evaluates their performance before recommending one.

## **8.5 Default Forecasting Strategy**

For the first implementation of SPIP, **Moving Average** is selected as the default forecasting model.

Reasons for selecting Moving Average include:

* Easy to understand.
* Stable for planners.
* Suitable for most materials with regular consumption.
* Simple to explain during business discussions.

This ensures that forecasting remains reliable while the system gradually learns from future business data.

## **8.6 Forecast Validation**

One common misunderstanding is that WMAPE can be calculated immediately after forecasting.

This is not possible.

Suppose today's date is:

```text
1 August
```

Historical consumption is available until:

```text
31 July
```

The system generates a forecast for:

```text
2 August

↓

16 August
```

Since the actual demand for these future dates is still unknown, there is nothing to compare the forecast against.

Therefore, WMAPE cannot be calculated immediately after generating a forecast.

## **8.7 Historical Backtesting**

To evaluate forecasting models before actual future data becomes available, SPIP uses **Historical Backtesting**.

The system pretends that it is standing at different points in the past and repeatedly performs forecasting.

Example:

Historical Consumption:

```text
January

February

March

April

May

June
```

The system performs the following process:

Step 1

Use:

```text
January

↓

March
```

Forecast:

```text
April
```

Compare with actual April consumption.

Step 2

Use:

```text
January

↓

April
```

Forecast:

```text
May
```

Compare with actual May consumption.

Step 3

Use:

```text
January

↓

May
```

Forecast:

```text
June
```

Compare with actual June consumption.

This process is repeated for every forecasting model.

The model producing the lowest forecasting error is considered the most reliable.

## **8.8 WMAPE Calculation**

Forecasting accuracy is measured using **Weighted Mean Absolute Percentage Error (WMAPE).**

The formula is:

```text
WMAPE

=

Σ |Actual − Forecast|

/

Σ Actual
```

Lower WMAPE indicates a more accurate forecasting model.

Example:

| Model                 | WMAPE |
| --------------------- | ----- |
| Moving Average        | 8%    |
| Exponential Smoothing | 11%   |
| Holt-Winters          | 14%   |

In this case, Moving Average becomes the recommended forecasting model.

## **8.9 Continuous Learning**

Forecasting is not a one-time activity.

Every time new consumption data is uploaded:

Actual Consumption

↓

Forecast Error

↓

WMAPE Updated

↓

Model Ranking Updated

↓

Recommended Model Updated

This creates a continuous learning cycle where forecasting improves over time.

## **8.10 Output of the Forecasting Engine**

The Forecasting Engine provides:

* 15-Day Forecast
* Recommended Forecast Model
* Forecast Accuracy
* WMAPE
* Forecast Trend
* Planning Demand

These outputs become direct inputs for the Requirement Resolution Engine.

# **9. Requirement Resolution Engine**

## **9.1 Purpose**

The Requirement Resolution Engine is a new module introduced in SPIP V2.

Its responsibility is to determine the **Final Planning Requirement** by combining multiple available planning inputs.

Instead of relying on a single data source, SPIP evaluates all available business information before deciding the material requirement.

This ensures that planning remains accurate even when one data source is unavailable.

## **9.2 Why Requirement Resolution is Needed**

Different business departments may provide different planning inputs.

For example:

* SAP provides historical consumption.
* IBP provides planned daily requirement.
* Manual uploads provide monthly requirement.
* Forecasting predicts future demand.

If these values differ, the system must decide which requirement should be used for planning.

The Requirement Resolution Engine performs this decision-making process.

## **9.3 Input Sources**

The engine considers:

* Forecasted Demand
* IBP Daily Requirement
* Monthly Requirement
* Historical Consumption

The system combines these inputs to create one **Final Planning Requirement** used by all downstream planning modules.

## **9.4 Business Logic**

The planner should never work with four different demand values.

Instead, SPIP generates one consolidated planning requirement.

Example:

```text
Historical Consumption

↓

Forecast

↓

IBP Requirement

↓

Monthly Requirement

↓

Final Planning Requirement
```

Every planning module uses this final value.

## **9.5 Benefits**

This approach:

* Eliminates conflicting planning values.
* Keeps procurement recommendations consistent.
* Simplifies planner decision-making.
* Ensures all planning modules work from the same requirement.

# **10. Raw Material (RM) Planning Engine**

## **10.1 Purpose**

Raw Material planning is one of the biggest architectural changes introduced in SPIP V2.

Unlike the previous version, RM planning no longer depends entirely on the Bill of Materials (BOM).

Instead, it uses **RM Totality Mapping**, which is based on historical material consumption.

## **10.2 Why BOM Cannot Be Used for RM**

In practical manufacturing environments, Raw Material consumption is highly dynamic.

Factors such as:

* Process variation
* Material quality
* Production adjustments
* Manufacturing losses

cause actual RM usage to differ from the theoretical BOM.

Therefore, relying entirely on BOM may produce inaccurate procurement recommendations.

## **10.3 RM Totality Concept**

Instead of exact BOM quantities, SPIP groups Finished Goods that consume similar Raw Materials.

Example:

```text
FG-1001

FG-1002

FG-1005

↓

RM Group A
```

Historical consumption of this group is analysed to estimate future RM requirements.

This approach is referred to as **RM Totality Mapping**.

## **10.4 RM Requirement Calculation**

The RM Planning Engine combines:

* Historical Consumption
* Forecast
* Final Planning Requirement
* RM Totality Mapping

to estimate the quantity of Raw Material required for future production.

This approach produces more practical planning recommendations than relying solely on BOM.

## **10.5 RM Planning Output**

The engine generates:

* Estimated RM Requirement
* RM Criticality
* RM Dependency
* Procurement Requirement
* Production Impact

# **11. Packaging Material (PM) Planning Engine**

## **11.1 Purpose**

Unlike Raw Materials, Packaging Materials are generally more stable.

Their quantities usually remain consistent for a Finished Good.

Therefore, Packaging Material planning continues to use the Bill of Materials (BOM).

## **11.2 BOM-Based Planning**

SPIP calculates PM requirements using the standard BOM.

Example:

```text
FG-1001

↓

PM-2001

↓

10 Units
```

The calculated quantity becomes the default planning value.

## **11.3 Planner Override**

Although BOM is considered reliable for Packaging Materials, practical situations may require manual adjustments.

Therefore, SPIP provides an **Edit** option allowing planners to modify PM quantities whenever necessary.

The updated quantity becomes the planning quantity for that planning cycle.

This combines the accuracy of BOM with the flexibility required in real manufacturing environments.

## **11.4 Output of PM Planning**

The PM Planning Engine provides:

* PM Requirement
* PM Dependency
* PM Criticality
* PM Procurement Requirement

These outputs, together with the RM Planning outputs, become inputs for the Dependency Intelligence Engine discussed in the next section.

**Part 4** will cover the core planning intelligence of SPIP:

* Dependency Intelligence Engine
* Finished Goods Production Readiness
* Planning Engine
* Constraint-Based Procurement Engine
* Proactive & Reactive Procurement Recommendations

This section explains how SPIP converts calculated material requirements into actionable procurement decisions for planners.

# **SPIP V2 – Functional Business Logic & Planning Architecture Specification**

# **12. Dependency Intelligence Engine**

## **12.1 Purpose**

The Dependency Intelligence Engine identifies how the shortage of one material can affect the production of one or more Finished Goods.

Instead of only identifying that a material is critical, the system also answers:

* Which Finished Goods depend on this material?
* How many Finished Goods will be affected?
* Is the shortage caused by a Raw Material or a Packaging Material?
* Can production continue despite the shortage?

This helps planners understand the business impact of every material shortage.

## **12.2 Why Dependency Analysis is Important**

Imagine that RM-1001 becomes critical.

Simply displaying:

```text
RM-1001

Status : Critical
```

does not help the planner understand the actual impact.

Instead, SPIP should display:

```text
RM-1001

Status : Critical

Used By:

FG-1001

FG-1003

FG-1007
```

Now the planner immediately understands which Finished Goods are at risk.

This allows procurement to be prioritised based on production impact rather than inventory alone.

## **12.3 RM Dependency Logic**

Unlike the previous SPIP version, RM dependency is **not calculated using BOM**.

Instead, it is calculated using **RM Totality Mapping**.

The process is:

```text
Historical Consumption

↓

RM Totality Group

↓

Finished Goods Group

↓

Affected Finished Goods
```

Example:

```text
RM-1001

↓

Industrial Explosive Group

↓

FG-1001

FG-1002

FG-1005
```

If RM-1001 becomes unavailable, the system immediately identifies the Finished Goods that may be affected.

This approach reflects actual business consumption rather than theoretical BOM values.

## **12.4 PM Dependency Logic**

Packaging Material dependency continues to use the standard BOM because Packaging Materials are relatively stable.

The process is:

```text
Finished Good

↓

Packaging BOM

↓

Packaging Material
```

Example:

```text
FG-1001

↓

PM-2001

↓

10 Units
```

If PM-2001 becomes unavailable, the corresponding Finished Goods are automatically marked as affected.

## **12.5 Dependency Analysis Output**

For every material, SPIP provides:

* Material Type (RM or PM)
* Dependent Finished Goods
* Number of Finished Goods affected
* Material Status
* Production Impact

This information is used by the Production Readiness Engine.

# **13. Production Readiness Engine**

## **13.1 Purpose**

The Production Readiness Engine determines whether a Finished Good can currently be manufactured based on the availability of all required Raw Materials and Packaging Materials.

Instead of only displaying inventory information, this module provides a production-oriented view of material availability.

## **13.2 Why Production Readiness is Required**

Inventory status and production status are different.

A Finished Good may have zero inventory but still be fully producible because all its required components are available.

Similarly, a Finished Good may have good inventory today but future production may stop if one critical component becomes unavailable.

Therefore, SPIP evaluates production readiness independently.

## **13.3 Production Readiness Logic**

The engine evaluates:

* RM Availability
* PM Availability
* Material Criticality
* Dependency Analysis
* Final Planning Requirement

Based on these inputs, one of the following statuses is assigned:

🟢 Ready to Produce

All required RM and PM are available.

🟡 Limited Production

Production can continue, but one or more materials are approaching shortage.

🟠 RM Shortage

Production is affected because one or more Raw Materials are unavailable.

🟠 PM Shortage

Production is affected because one or more Packaging Materials are unavailable.

🔴 Production Blocked

Production cannot continue because multiple critical components are unavailable.

## **13.4 Production Summary**

Every Finished Good displays a summary similar to:

```text
FG-1001

Production Readiness

✓ RM Available : 12 / 12

✓ PM Available : 5 / 5

Overall Status

🟢 Ready to Produce
```

If shortages exist:

```text
FG-1001

Production Readiness

✓ PM Available : 5 / 5

✗ RM Available : 10 / 12

Overall Status

🟠 RM Shortage
```

This allows planners to identify production problems without opening detailed BOM information.

## **13.5 Production Readiness Output**

The module provides:

* Overall Production Status
* RM Availability
* PM Availability
* Blocking Materials
* Production Impact

These outputs are displayed in the Finished Goods workspace.

# **14. Planning Engine**

## **14.1 Purpose**

The Planning Engine is the central decision-making module of SPIP.

All previous modules prepare planning parameters, while the Planning Engine combines them to determine the actual procurement requirement.

It answers one important question:

**"What should the planner procure today?"**

## **14.2 Inputs**

The Planning Engine receives information from:

* Consumption Intelligence
* Inventory Intelligence
* Forecasting Engine
* Requirement Resolution Engine
* RM Planning
* PM Planning
* Production Readiness
* Safety Stock
* Trigger Levels (1 & 2)

## **14.3 Gross Requirement**

The first calculation determines the total material requirement before considering available inventory.

Gross Requirement represents the total quantity expected to be required for future production.

## **14.4 Net Requirement**

The system then subtracts available inventory from the Gross Requirement.

Conceptually:

```text
Gross Requirement

−

Available Inventory

=

Net Requirement
```

Net Requirement represents the quantity that still needs to be procured.

## **14.5 Material Criticality**

Using Net Requirement, Trigger-1/2, Safety Stock-1/2, and Inventory Health, SPIP classifies every material into one of four planning categories:

🟢 Healthy

Inventory is sufficient.

🟡 Low Stock

Inventory should be monitored.

🟠 Reorder Required

Procurement should begin soon.

🔴 Critical

Immediate procurement action is recommended.

These statuses are displayed throughout the Planning Overview.

## **14.6 Planning Output**

The Planning Engine provides:

* Gross Requirement
* Net Requirement
* Material Criticality
* Procurement Requirement
* Planning Priority

These outputs become direct inputs for the Procurement Recommendation Engine.

# **15. Procurement Recommendation Engine**

## **15.1 Purpose**

The Procurement Recommendation Engine converts planning requirements into practical procurement recommendations.

Rather than only identifying shortages, it tells the planner exactly what action should be taken.

## **15.2 Procurement Philosophy**

SPIP follows a **Proactive Planning** approach.

Instead of waiting until inventory becomes critical, procurement recommendations are generated immediately after every successful data upload.

This allows planners to initiate procurement before production is affected.

A manual **"Generate Procurement Plan"** button is also available whenever planners wish to regenerate recommendations.

## **15.3 Planning Constraints**

Procurement recommendations are generated only after evaluating all business constraints.

The engine considers:

* Final Planning Requirement
* Current Inventory
* Safety Stock 1 & 2
* Lead Time 1 & 2
* Vendor Capacity
* Vehicle Capacity
* Plant Storage Capacity
* Open Purchase Orders
* Gate Entries

Every recommendation satisfies these constraints before being presented to the planner.

## **15.4 Recommendation Generation**

For every material requiring procurement, SPIP recommends:

* Material Code
* Recommended Quantity
* Recommended Vendor
* Suggested Dispatch Date
* Expected Arrival Date
* Priority Level
* Reason for Recommendation

Example:

```text
Material : RM-1001

Recommended Quantity : 30 Tons

Recommended Vendor : Vendor A

Dispatch Date : 12 August

Expected Arrival : 17 August

Reason :

Critical Inventory

Lead Time 1 Trigger Reached
```

This provides planners with a complete procurement recommendation rather than only a warning.

## **15.5 Proactive and Reactive Procurement**

SPIP supports two planning modes.

### **Proactive Planning**

Automatically generated after every data upload.

Based on:

* Forecast
* Planning Requirements
* Lead Time
* Inventory
* Business Constraints

This is the preferred planning approach.

### **Reactive Planning**

Triggered whenever unexpected shortages occur.

Examples include:

* Sudden increase in consumption
* Emergency customer order
* Vendor delay
* Material stockout

Reactive planning allows planners to respond immediately to unforeseen situations.

Both planning modes remain available, allowing planners to decide which approach is appropriate.

## **15.6 Output of the Procurement Recommendation Engine**

The Procurement Recommendation Engine provides:

* Procurement Plan
* Recommended Vendor
* Recommended Quantity
* Suggested Dispatch Date
* Expected Arrival Date
* Procurement Priority
* Planning Justification

These recommendations are then forwarded to the Allocation Engine discussed in the next section.

**Part 5** will complete the Functional Business Logic Specification by covering:

* Vendor Allocation Engine
* Notification & Approval Workflow
* Dashboard Logic
* Report Generation
* Business Rules & Exception Handling
* Future Scope of SPIP V2

This final section will explain how planners interact with the system, approve recommendations, communicate with vendors, and use dashboards and reports to support day-to-day planning decisions.

# **SPIP V2 – Functional Business Logic & Planning Architecture Specification**

# **16. Vendor Allocation Engine**

## **16.1 Purpose**

The Vendor Allocation Engine converts procurement recommendations into actual allocation plans for suppliers.

Once the Planning Engine has identified which materials need to be procured, the Vendor Allocation Engine helps planners decide:

* Which vendor should receive the order?
* How much quantity should each vendor supply?
* When should the material be dispatched?
* When should the material reach the plant?

Unlike traditional systems, SPIP does not directly place procurement orders. Instead, it generates allocation recommendations which are reviewed and approved by the planner.

## **16.2 Allocation Philosophy**

SPIP follows a **Planner-in-the-Loop** approach.

The system automatically generates recommendations, but the planner always remains responsible for the final allocation decision.

The workflow is:

```text
Planning Recommendation

↓

Planner Review

↓

Modify (Optional)

↓

Approve

↓

Vendor Notification

↓

Allocation Tracking
```

This ensures business flexibility while reducing manual planning effort.

## **16.3 Proactive Allocation**

Proactive Allocation is the preferred planning approach.

It is generated automatically whenever:

* New business data is uploaded.
* The planner manually clicks **Generate Planning**.
* Planning parameters change significantly.

The recommendation is prepared before any material becomes critical.

The recommendation considers:

* Current Inventory
* Forecast
* Lead Time
* Vendor Capacity
* Vehicle Capacity
* Storage Capacity
* Safety Stock
* Purchase Orders
* Gate Entries

The objective is to avoid shortages before they occur.

## **16.4 Reactive Allocation**

Reactive Allocation is used whenever unexpected situations occur.

Examples include:

* Sudden increase in consumption
* Emergency customer orders
* Vendor delay
* Material damage
* Unexpected stockout

Reactive Allocation allows the planner to respond immediately to changing business conditions.

Both Proactive and Reactive Allocation remain available within the system, allowing planners to choose the most appropriate approach.

## **16.5 Planner Modification**

Business situations may require changes to the automatically generated recommendation.

Therefore, SPIP provides an Edit option where the planner can modify:

* Vendor
* Quantity
* Dispatch Date
* Priority
* Remarks

The modified allocation becomes the approved business plan.

## **16.6 Vendor Communication**

After planner approval, SPIP automatically prepares vendor communication.

Future versions of the system will support:

* Email Notification
* In-App Vendor Notification
* Vendor Portal Integration

This ensures that approved allocations are communicated immediately without requiring separate manual emails.

## **16.7 Allocation Tracking**

Every allocation moves through different stages.

Typical statuses include:

* Draft
* Recommended
* Approved
* Sent to Vendor
* Vendor Accepted
* Material In Transit
* Delivered
* Closed

This provides complete visibility into the procurement lifecycle.

# **17. Dashboard**

## **17.1 Purpose**

The Dashboard provides planners with a quick overview of the current planning situation.

Rather than displaying raw business data, the dashboard highlights information that requires immediate attention.

Its primary objective is to help planners identify risks and take action quickly.

## **17.2 Dashboard Philosophy**

The dashboard should answer important business questions rather than simply displaying statistics.

Examples include:

* Which materials are currently critical?
* Which Finished Goods are at production risk?
* Which vendors require allocations?
* Which procurement recommendations need approval?
* Which materials have become critical today?

The dashboard should always guide the planner towards the next business decision.

## **17.3 Material Criticality View**

The dashboard displays Material Criticality separately for:

* Raw Materials (RM)
* Packaging Materials (PM)

The planner can filter the dashboard using:

* All
* RM
* PM

This keeps the planning workspace focused only on procurement materials.

Finished Goods continue to have their own dedicated workspace.

## **17.4 Production Readiness View**

The Finished Goods Workspace displays Production Readiness instead of inventory health.

Possible statuses include:

🟢 Ready to Produce

🟡 Limited Production

🟠 RM Shortage

🟠 PM Shortage

🔴 Production Blocked

The planner can immediately identify which Finished Goods require attention.

## **17.5 Dashboard KPIs**

The dashboard may display:

* Total Materials
* Critical Materials
* Materials Requiring Reorder
* Procurement Recommendations
* Pending Vendor Allocations
* Production Ready Finished Goods
* Blocked Finished Goods

These KPIs provide an instant summary of the current planning environment.

# **18. Reports**

## **18.1 Purpose**

Reports provide planners and management with structured business information for analysis and decision-making.

All reports are generated using the latest planning calculations.

## **18.2 Available Reports**

SPIP supports reports such as:

* Planning Summary
* Inventory Report
* Consumption Report
* Forecast Report
* Procurement Recommendation Report
* Vendor Allocation Report
* Production Readiness Report
* Material Criticality Report

Additional reports can be added in future without affecting the planning engine.

## **18.3 Export Formats**

Reports can be exported in:

* Microsoft Excel (.xlsx)
* CSV (.csv)

The exported reports preserve all calculated planning values and are suitable for further analysis or sharing with business teams.

# **19. Notification & Approval Workflow**

## **19.1 Purpose**

The Notification System keeps planners informed whenever important planning events occur.

Instead of requiring users to continuously monitor every module, SPIP automatically generates notifications for significant business events.

## **19.2 Notification Types**

Examples include:

* New Procurement Recommendation
* Allocation Approval Required
* Material Becomes Critical
* Production Blocked
* New Report Generated
* Data Upload Completed

## **19.3 Notification Behaviour**

Unread notifications are displayed using a notification counter.

Example:

```text
🔔 3
```

After the planner views the notification, it is automatically marked as read and the counter decreases accordingly.

Similarly, the Manager Queue displays an indicator only when pending approvals exist.

Once all pending approvals have been reviewed, the indicator disappears automatically.

# **20. Business Rules & Exception Handling**

## **20.1 Purpose**

Business planning depends on accurate and complete data.

Whenever required information is unavailable, SPIP does not stop working silently. Instead, it clearly informs the planner about missing data and explains its impact.

## **20.2 Missing Data Rules**

Examples include:

If Vendor Capacity is unavailable:

```text
Vendor Capacity not available.

Vendor recommendation cannot be generated.
```

If Storage Capacity is unavailable:

```text
Plant Storage Capacity not uploaded.

Storage constraint cannot be evaluated.
```

If IBP data is unavailable:

```text
IBP data unavailable.

Forecast-based planning will be used.
```

This allows the planner to understand why certain recommendations may be incomplete.

## **20.3 Data Validation Rules**

SPIP validates:

* Mandatory columns
* Material Codes
* Plant Codes
* Vendor Codes
* Duplicate records
* Missing values
* Invalid quantities
* Invalid dates

Only validated information enters the planning engine.

## **20.4 Planner Override**

Although SPIP generates intelligent recommendations, planners always retain the authority to override system decisions.

This includes:

* Procurement Quantity
* Vendor Selection
* Dispatch Date
* PM Quantity Adjustment
* Allocation Approval

The system records these changes to maintain planning transparency.

# **21. Future Scope**

SPIP V2 establishes a strong foundation for enterprise planning.

Future enhancements may include:

* Direct SAP Integration
* Live IBP Synchronization
* Vendor Portal
* Automatic Purchase Requisition Generation
* AI-Based Procurement Recommendations
* Route Optimization
* Vehicle Scheduling
* Advanced Forecasting Models
* Multi-Plant Optimization
* Supply Chain Simulation
* Power BI Integration
* Mobile Application
* Approval Workflow Automation

These enhancements can be added without changing the core planning architecture.

# **22. Conclusion**

SPIP V2 transforms the existing application from a reporting-focused system into a complete enterprise planning platform.

The platform combines historical consumption, inventory analysis, forecasting, statistical planning, RM Totality Mapping, PM BOM planning, dependency intelligence, procurement recommendations, and vendor allocation into a single decision-support system.

Rather than replacing the planner, SPIP acts as an intelligent assistant that continuously analyses business data and recommends the most suitable planning actions.

By integrating data from SAP, IBP, and manual business inputs, the platform provides planners with a unified environment for procurement planning, production readiness analysis, inventory management, and supply chain decision-making.

The proposed architecture is scalable, modular, and designed to support future business growth while maintaining flexibility for evolving planning requirements.

# **End of Functional Business Logic & Planning Architecture Specification**

**Document Version:** 1.0 (Draft)

**Status:** Ready for Business Review & Discussion

**Next Phase:** Business Requirement Document (BRD) → Technical Design Document (TDD) → SPIP V2 Implementation Roadmap

