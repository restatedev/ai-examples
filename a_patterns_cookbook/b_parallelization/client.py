import httpx

stakeholders = [
    """Customers:
    - Price sensitive
    - Want better tech
    - Environmental concerns""",

    """Employees:
    - Job security worries
    - Need new skills
    - Want clear direction""",

    """Investors:
    - Expect growth
    - Want cost control
    - Risk concerns""",

    """Suppliers:
    - Capacity constraints
    - Price pressures
    - Tech transitions"""
]

data = {
    "prompt": """Analyze how market changes will impact this stakeholder group.
    Provide specific impacts and recommended actions.
    Format with clear sections and priorities.""",
    "inputs": stakeholders
}

headers = {"Content-Type": "application/json", "Accept": "application/json"}

r = httpx.post(
    "http://localhost:8080/ParallelizationService/run_in_parallel",
    json=data,
    headers=headers,
    timeout=60,
)

if r.is_error:
    raise ValueError(f"{r.status_code} : {r.text}")

[print(item) for item in r.json()]

"""
The output should be something along the lines of: 

**Analysis of Market Changes Impacting Customers**

**1. Market Changes:**
   - **Rising Costs of Raw Materials:** Global supply chain disruptions and inflationary pressures are leading to increased costs for raw materials, which may result in higher prices for end products.
   - **Technological Advancements:** Rapid advancements in technology are continuously reshaping product offerings, with a focus on smart, connected, and efficient solutions.
   - **Increased Environmental Regulations:** Governments and international bodies are implementing stricter environmental regulations, pushing companies to adopt sustainable practices.

**2. Specific Impacts on Customers:**

   **a. Price Sensitivity:**
   - **Impact:** Customers may face higher prices for products and services due to increased production costs.
   - **Recommended Action:** Companies should explore cost-saving measures and efficiencies to minimize price increases. Offering tiered pricing or value-based options can help cater to different budget levels.

   **b. Desire for Better Technology:**
   - **Impact:** Customers expect the latest technology in products, which can drive demand for frequent upgrades and innovations.
   - **Recommended Action:** Invest in R&D to stay ahead of technological trends. Regularly update product lines with new features and improvements. Communicate the value of technological advancements to justify any price increases.

   **c. Environmental Concerns:**
   - **Impact:** Customers are increasingly prioritizing eco-friendly products and practices, influencing their purchasing decisions.
   - **Recommended Action:** Adopt sustainable practices across the supply chain. Highlight eco-friendly initiatives and certifications in marketing efforts. Develop and promote products with reduced environmental impact.

**3. Prioritized Recommended Actions:**

   **Priority 1: Enhance Value Proposition**
   - Focus on delivering high-quality, technologically advanced products that justify their price.
   - Implement loyalty programs or discounts for repeat customers to maintain competitiveness.

   **Priority 2: Strengthen Sustainability Efforts**
   - Invest in sustainable materials and production processes.
   - Engage in transparent communication about environmental efforts and achievements.

   **Priority 3: Optimize Cost Management**
   - Streamline operations to reduce costs without compromising quality.
   - Explore alternative suppliers or materials to mitigate the impact of rising raw material costs.

**Conclusion:**
To effectively address the impacts of market changes on price-sensitive, tech-savvy, and environmentally conscious customers, companies must balance cost management with innovation and sustainability. By prioritizing these actions, businesses can enhance customer satisfaction and loyalty while navigating the evolving market landscape.
### Analysis of Market Changes Impact on Employees

#### 1. Job Security Worries

**Impact:**
- **Increased Anxiety and Stress:** Employees may experience heightened anxiety due to fears of layoffs or restructuring, which can lead to decreased productivity and morale.
- **Reduced Loyalty and Engagement:** Concerns over job security can result in reduced loyalty to the company, as employees may begin seeking more stable opportunities elsewhere.

**Recommended Actions:**
- **Transparent Communication:** Regularly update employees on the company's financial health and strategic direction to alleviate uncertainty.
- **Job Security Programs:** Implement initiatives such as cross-training and internal mobility programs to reassure employees of their value and potential within the company.
- **Support Systems:** Provide access to mental health resources and counseling to help employees manage stress and anxiety.

#### 2. Need for New Skills

**Impact:**
- **Skill Gaps:** Rapid market changes may render existing skills obsolete, creating a gap between current employee capabilities and market demands.
- **Increased Training Costs:** The company may face increased costs associated with upskilling or reskilling employees to meet new market requirements.

**Recommended Actions:**
- **Skill Development Programs:** Invest in comprehensive training and development programs focused on emerging skills relevant to market changes.
- **Partnerships with Educational Institutions:** Collaborate with universities and training providers to offer courses and certifications that align with industry trends.
- **Mentorship and Coaching:** Establish mentorship programs to facilitate knowledge transfer and skill development within the organization.

#### 3. Desire for Clear Direction

**Impact:**
- **Uncertainty and Confusion:** Lack of clear direction can lead to confusion about roles and responsibilities, hindering effective performance.
- **Decreased Motivation:** Employees may feel demotivated if they do not understand how their work contributes to the company's goals.

**Recommended Actions:**
- **Strategic Vision Communication:** Clearly articulate the company's strategic vision and how each department and role contributes to achieving it.
- **Regular Feedback and Updates:** Implement regular check-ins and feedback sessions to ensure employees are aligned with company objectives and understand their role in achieving them.
- **Leadership Development:** Train leaders to effectively communicate and inspire their teams, fostering a sense of purpose and direction.

### Priorities for Implementation

1. **Immediate Priority: Transparent Communication**
   - Establish regular communication channels to address job security concerns and provide updates on company direction.

2. **Short-term Priority: Skill Development Initiatives**
   - Launch skill development programs and partnerships to address skill gaps and prepare employees for future market demands.

3. **Long-term Priority: Leadership and Mentorship Programs**
   - Develop leadership and mentorship programs to ensure ongoing alignment with company goals and foster a supportive work environment.

By addressing these areas with targeted actions, the company can mitigate the negative impacts of market changes on employees, enhancing job security, skill relevance, and clarity of direction.
### Analysis of Market Changes Impacting Investors

#### 1. Market Growth Expectations

**Impact:**
- **Positive Impact:** Investors expecting growth will benefit from market expansions, increased revenues, and potential capital gains. Sectors like technology, renewable energy, and healthcare are projected to grow, offering lucrative opportunities.
- **Negative Impact:** If growth expectations are unmet, investor confidence may decline, leading to reduced investments and potential sell-offs.

**Recommended Actions:**
- **Diversification:** Encourage diversification across high-growth sectors to mitigate risks associated with underperformance in any single industry.
- **Regular Updates:** Provide frequent updates on growth metrics and market trends to maintain investor confidence and manage expectations.

#### 2. Cost Control

**Impact:**
- **Positive Impact:** Effective cost control can lead to improved profit margins, enhancing investor returns. Companies that manage costs well are more resilient to economic downturns.
- **Negative Impact:** Poor cost management can erode profits, leading to investor dissatisfaction and potential withdrawal of investments.

**Recommended Actions:**
- **Efficiency Audits:** Conduct regular audits to identify areas for cost reduction without compromising quality or growth.
- **Technology Investment:** Invest in technology that enhances operational efficiency and reduces long-term costs.

#### 3. Risk Concerns

**Impact:**
- **Positive Impact:** Addressing risk concerns can lead to increased investor trust and long-term investment stability. Transparent risk management strategies can attract risk-averse investors.
- **Negative Impact:** High-risk exposure without adequate mitigation strategies can lead to investor anxiety and potential capital flight.

**Recommended Actions:**
- **Risk Assessment:** Implement comprehensive risk assessment frameworks to identify and mitigate potential threats.
- **Communication:** Maintain open communication channels to inform investors about risk management strategies and contingency plans.

### Priorities for Investors

1. **Growth Management:** Prioritize strategies that align with growth expectations, ensuring that investments are directed towards sectors with strong growth potential.
2. **Cost Efficiency:** Focus on maintaining and improving cost control measures to enhance profitability and investor satisfaction.
3. **Risk Mitigation:** Develop robust risk management frameworks to address investor concerns and ensure long-term investment security.

By addressing these priorities, investors can better navigate market changes, optimize returns, and maintain confidence in their investment strategies.
### Analysis of Market Changes Impacting Suppliers

#### 1. Capacity Constraints

**Impact:**
- **Increased Lead Times:** Suppliers may face challenges in meeting demand due to limited production capacity, leading to longer lead times.
- **Potential Loss of Business:** Customers may seek alternative suppliers if their needs are not met promptly.
- **Operational Strain:** Overutilization of existing resources can lead to increased wear and tear, potentially causing operational inefficiencies and higher maintenance costs.

**Recommended Actions:**
- **Invest in Capacity Expansion:** Prioritize investments in expanding production capabilities to meet growing demand.
- **Optimize Production Processes:** Implement lean manufacturing techniques to improve efficiency and reduce waste.
- **Strengthen Supplier Relationships:** Collaborate with secondary suppliers to create a more flexible supply chain.

#### 2. Price Pressures

**Impact:**
- **Reduced Profit Margins:** Rising costs of raw materials and labor can squeeze profit margins.
- **Competitive Disadvantage:** Inability to absorb or pass on costs may lead to a loss of competitive edge.
- **Customer Pushback:** Price increases may lead to customer dissatisfaction or loss of business.

**Recommended Actions:**
- **Cost Management Strategies:** Implement cost-saving measures such as bulk purchasing and renegotiating supplier contracts.
- **Value-Added Services:** Differentiate offerings by providing additional services or quality improvements to justify price increases.
- **Dynamic Pricing Models:** Consider adopting flexible pricing strategies that can adjust to market conditions.

#### 3. Tech Transitions

**Impact:**
- **Adaptation Challenges:** Suppliers may struggle to keep up with technological advancements, leading to obsolescence.
- **Investment Requirements:** Significant capital may be needed to upgrade technology and infrastructure.
- **Skill Gaps:** Workforce may require retraining to handle new technologies effectively.

**Recommended Actions:**
- **Invest in R&D:** Allocate resources to research and development to stay ahead of technological trends.
- **Partnerships with Tech Firms:** Collaborate with technology companies to integrate new solutions seamlessly.
- **Training Programs:** Develop comprehensive training programs to upskill employees and ensure smooth transitions.

### Priorities for Suppliers

1. **Capacity Expansion and Optimization:** Address capacity constraints as a top priority to ensure timely delivery and maintain customer satisfaction.
2. **Cost Management and Pricing Strategies:** Implement robust cost management practices and explore dynamic pricing models to mitigate price pressures.
3. **Technological Adaptation:** Invest in technology and workforce training to remain competitive and capitalize on tech transitions.

By focusing on these priorities, suppliers can better navigate market changes, maintain their competitive position, and ensure long-term sustainability.
"""
