# Data dictionary

## Files and scope

- **Orbit_operations.xlsx** contains full daily Orbit operations and staffing populations from April 1 through September 30, 2026. Its Call sample sheet contains 20,000 unique call records selected systematically across the period, plus 28 intentionally retained duplicate export rows. The sample is not total demand.
- **Quality_and_feedback.xlsx** contains selected QA reviews and voluntary post-call feedback. QA deliberately oversamples WN7 recovery-risk and long calls. Feedback deliberately oversamples WN7 outreach. All source event dates are at or before October 1, 2026. These are not random samples and should not be generalized as population rates without qualification.

## Shared join key

`Call ID` joins QA reviews and Customer feedback to the unique source records in the Call sample sheet. Duplicate export rows retain the same Call ID and are labeled in `Sample status`.

## Orbit_operations.xlsx

| Sheet | Grain | Key fields | Important use limits |
| --- | --- | --- | --- |
| Daily operations | Date and queue | Date, Queue | Full operational population. Use for demand, AHT, wait, abandonment, and tagged WN7 volume. Reason codes are not shown at call level here. |
| Call sample | Sampled call export row | Call ID, Sample row | Systematic sample only. Product and reason codes have bounded missing values. Remove duplicate Call IDs before record-level analysis. |
| Staffing | Date and queue | Date, Queue | Full workforce schedule and realized coverage. Coverage can constrain any learning rollout. |
| Product catalog | Product code | Product code | WN7 is the hub model with some affected batches. WNM-7 is a bundle containing that hub. In Daily operations, the WN7-related calls and WNM-7-related calls columns count answered contacts in mutually exclusive product-code buckets. Their sum is a proxy for answered WN7-containing contacts, not an eligibility or incident count. |

### Call sample fields

- **Serial verified** means the Guide recorded a serial check in Orbit from September 10 onward.
- **Eligible for recovery** is a retrospective analytic classification based on the affected pattern and serial range. Before September 10, it does not mean the Guide could use the approved recovery path.
- **Conversation path** describes observed disposition patterns. `Complete recovery` means the replacement was arranged and the Northstar Plus credit was attached. Incomplete recovery means an eligible call did not complete both required steps.
- **Northstar Plus attached** is a distinct step from arranging the replacement.
- **AHT minutes** equals talk, hold, and wrap time.

## Quality_and_feedback.xlsx

| Sheet | Grain | Key fields | Important use limits |
| --- | --- | --- | --- |
| QA reviews | Selected QA review | QA review ID, Call ID | Selection reason is explicit. Review date may lag call date. `Behavior count` is a checklist total, not a validated performance score. |
| Customer feedback | Voluntary response | Feedback ID, Call ID | Responses are nonrandom. Satisfaction reflects respondent experience and cannot prove a specific intervention caused it. |

## Known imperfections

- 28 duplicate call-export rows share stable Call IDs and are labeled `Duplicate export row`.
- About 0.8% of sampled product codes and 1.2% of reason codes are missing.
- QA and feedback do not cover every sampled call.
- Free text is synthetic, brief, and may use inconsistent language.
- Operational records end September 30. Dana's September 29 request does not establish that any response was implemented. Later planned actions are not completed data.

## Chronology

- August 31: Product confirms the WN7 issue.
- September 10: Replacement and Northstar Plus offer are approved.
- September 12: Specialist recovery pilot begins.
- September 21: General Care Beacon article is published.
