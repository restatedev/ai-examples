# Patterns for building resilient LLM-based apps and agents with Restate

These patterns show how you can use Restate to harden LLM-based routing decisions and tool executions.

They do not implement end-to-end agents, but serve as small self-contained patterns that can be mixed and matched to build more complex workflows.

The patterns included here:
- [Chaining LLM calls](chaining/service.py): Refine the results by calling the LLM iteratively with its own output.
- [Parallelizing tool calls](parallelization/service.py): Call multiple tools in parallel and wait for their results in a durable way. Tool calls are retried if they fail, and the results are persisted.
- [Dynamic routing based on LLM output](routing/service.py): Route the execution to different tools based on the LLM's output. Routing decisions are persisted and can be retried.
- [Orchestrator-worker pattern](orchestrator_workers/service.py): A resilient orchestration workflow in which a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and analyzes their results.
- [Evaluator-optimizer pattern](evaluator_optimizer/service.py): Let the LLM generate a response, and ask another LLM to evaluate the response, and let them iterate on it.
- [Human-in-the-loop pattern](human_in_the_loop/service.py): An LLM generates a response, and then a human can review and approve the response before the LLM continues with the next step.

A part of these patterns are based on Anthropic's [agents cookbook](https://github.com/anthropics/anthropic-cookbook/tree/main/patterns/agents).

## Why Restate?

The benefits of using Restate here are:
- 🔁 **Automatic retries** of failed tasks: LLM API down, timeouts, long-running tasks, infrastructure failures, etc. Restate guarantees all tasks run to completion exactly once.
- ✅ **Recovery of previous progress**: After a failure, Restate recovers the progress the execution did before the crash. 
It persists routing decisions, tool execution outcomes, and deterministically replays them after failures, as opposed to executing them again. 
- 🧠 **Exactly-once execution** - Automatic deduplication of requests and tool executions via idempotency keys.
- 💾 **Persistent memory** - Maintain session state across infrastructure events.
The state can be queried from the outside. Stateful sessions are long-lived and can be resumed at any time.
- 🎮 **Task control** - Cancel tasks, query status, re-subscribe to ongoing tasks, and track progress across failures, time, and processes.

These benefits are best portrayed in the following patterns:

| Pattern                     | Retries & recovery | Exactly-once execution | Persistent memory | 
|-----------------------------|--------------------|------------------------|-------------------|
| Chaining LLM calls          | ✅                  | ✅                      |                   |              
| Parallelizing tool calls    | ✅                  | ✅                      |                   |              
| Dynamic routing             | ✅                  | ✅                      |                   |              
| Orchestrator-worker pattern | ✅                  | ✅                      |                   |              
| Evaluator-optimizer pattern | ✅                  | ✅                      |                   |              
| Human-in-the-loop pattern   | ✅                  | ✅                      | ✅                 |              


## Running the examples

1. Export your OpenAI or Anthrophic API key as an environment variable:
    ```shell
    export OPENAI_API_KEY=your_openai_api_key
    ```
    or:
    ```shell
    export ANTHROPIC_API_KEY=your_anthropic_api_key
    ```
2. [Start the Restate Server](https://docs.restate.dev/develop/local_dev) in a separate shell:
    ```shell
    restate-server
    ```
3. Start the services:
    ```shell
    uv run .
    ```
4. Register the services (use `--force` if you already had another deployment registered at 9080): 
    ```shell
    restate -y deployments register localhost:9080 --force
    ```

### Chaining LLM calls
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](chaining/service.py)

Refine the results by calling the LLM iteratively with its own output.

Send an HTTP request to the service via the [UI playground](http://localhost:9070/ui/overview?servicePlayground=CallChainingService&service=CallChainingService#/operations/run):
![img.png](img.png)

You see in the UI how the LLM is called multiple times, and how the results are refined step by step:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/chaining.png" alt="Chaining LLM calls - UI"/>

<details>
<summary>View output</summary>

```text
Step 1:
92 points: customer satisfaction  
45 percent: revenue growth  
23 percent: market share  
5 percent: customer churn  
43 USD: user acquisition cost  
78 percent: product adoption rate  
87 points: employee satisfaction  
34 percent: operating margin

Step 2:
92 percent: customer satisfaction  
45 percent: revenue growth  
23 percent: market share  
5 percent: customer churn  
43.00 USD: user acquisition cost  
78 percent: product adoption rate  
87 percent: employee satisfaction  
34 percent: operating margin

Step 3:
Here's the sorted list:

92 percent: customer satisfaction
87 percent: employee satisfaction
78 percent: product adoption rate
45 percent: revenue growth
43.00 USD: user acquisition cost
34 percent: operating margin
23 percent: market share
5 percent: customer churn

Step 4:
Here's the sorted data formatted as a markdown table:

| Metrics                  | Values   |
|--------------------------|----------|
| customer satisfaction    | 92%      |
| employee satisfaction    | 87%      |
| product adoption rate    | 78%      |
| revenue growth           | 45%      |
| user acquisition cost    | 43.00 USD|
| operating margin         | 34%      |
| market share             | 23%      |
| customer churn           | 5%       |

```

</details>

### Parallelizing tool calls
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](parallelization/service.py)

Call multiple tools in parallel and wait for their results in a durable way. Tool calls are retried if they fail, and the results are persisted.

Send an HTTP request to the service by running the [client](parallelization/client.py):

```shell
uv run parallelization_client
```

You see in the UI how the different tasks are executed in parallel: 

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/parallel.png" alt="Chaining LLM calls - UI"/>

Once all tasks are done, the results are aggregated and returned to the client.

<details>
<summary>View output</summary>

```text
**Stakeholder Analysis: Customers**

**Priorities:**
1. Price Sensitivity
2. Desire for Better Technology
3. Environmental Concerns

**Market Changes Impacting Customers:**

1. **Economic Fluctuations:**
   - **Impact:** Economic downturns or inflation can increase the cost of goods and services, affecting price-sensitive customers. Conversely, economic growth can lead to increased disposable income, allowing customers to prioritize better technology and environmentally friendly products.
   - **Recommended Actions:** 
     - **Short-term:** Implement dynamic pricing strategies and offer discounts or loyalty programs to retain price-sensitive customers.
     - **Long-term:** Invest in cost-effective technologies and supply chain efficiencies to maintain competitive pricing.

2. **Technological Advancements:**
   - **Impact:** Rapid technological advancements can lead to obsolescence of current products, pushing customers to seek the latest innovations.
   - **Recommended Actions:**
     - **Short-term:** Regularly update product lines with incremental improvements and communicate these enhancements effectively to customers.
     - **Long-term:** Invest in R&D to stay ahead of technological trends and collaborate with tech partners to integrate cutting-edge features.

3. **Environmental Regulations and Trends:**
   - **Impact:** Increasing environmental awareness and regulations can shift customer preferences towards sustainable products.
   - **Recommended Actions:**
     - **Short-term:** Highlight existing eco-friendly features of products and improve transparency about environmental impact.
     - **Long-term:** Develop a sustainability strategy that includes reducing carbon footprint, using recyclable materials, and obtaining eco-certifications.

**Specific Impacts and Recommended Actions:**

1. **Price Sensitivity:**
   - **Impact:** Customers may switch to competitors if prices rise significantly.
   - **Recommended Actions:**
     - **Priority 1:** Implement tiered pricing models to cater to different budget levels.
     - **Priority 2:** Enhance value propositions by bundling products or services.

2. **Desire for Better Technology:**
   - **Impact:** Customers may delay purchases until newer models are available.
   - **Recommended Actions:**
     - **Priority 1:** Launch marketing campaigns that emphasize the unique technological benefits of current offerings.
     - **Priority 2:** Offer trade-in programs to encourage upgrades and maintain customer loyalty.

3. **Environmental Concerns:**
   - **Impact:** Customers may prefer brands with strong environmental commitments.
   - **Recommended Actions:**
     - **Priority 1:** Increase investment in sustainable product development and packaging.
     - **Priority 2:** Engage in community and environmental initiatives to build brand reputation.

**Conclusion:**
To effectively address the evolving market changes, businesses must prioritize maintaining competitive pricing, staying at the forefront of technological innovation, and committing to sustainability. By aligning strategies with customer priorities, companies can enhance customer satisfaction and loyalty, ultimately driving long-term success.
### Analysis of Market Changes Impacting Employees

#### 1. Job Security Worries

**Impact:**
- **Automation and AI Integration:** As companies increasingly adopt automation and AI technologies, there is a potential reduction in demand for certain job roles, particularly those involving repetitive tasks.
- **Economic Fluctuations:** Economic downturns or shifts in consumer demand can lead to restructuring or downsizing, affecting job security.
- **Industry Disruption:** Emerging technologies and new business models can disrupt traditional industries, leading to job displacement.

**Recommended Actions:**
- **Upskilling and Reskilling Programs:** Encourage participation in training programs to transition into roles less susceptible to automation.
- **Internal Mobility:** Promote internal job rotations to diversify skills and reduce dependency on a single role.
- **Transparent Communication:** Maintain open communication about company performance and strategic direction to alleviate uncertainty.

#### 2. Need for New Skills

**Impact:**
- **Technological Advancements:** Rapid technological changes require employees to continuously update their skill sets to remain relevant.
- **Shift to Digital Platforms:** Increased reliance on digital tools necessitates proficiency in new software and platforms.
- **Cross-Functional Skills:** There is a growing need for employees to possess a blend of technical and soft skills, such as problem-solving and adaptability.

**Recommended Actions:**
- **Continuous Learning Culture:** Foster a culture that values lifelong learning and provides access to online courses, workshops, and certifications.
- **Mentorship and Coaching:** Implement mentorship programs to facilitate knowledge transfer and skill development.
- **Skill Gap Analysis:** Conduct regular assessments to identify skill gaps and tailor training initiatives accordingly.

#### 3. Desire for Clear Direction

**Impact:**
- **Organizational Changes:** Frequent changes in company strategy or leadership can create confusion and uncertainty among employees.
- **Lack of Communication:** Insufficient communication regarding company goals and employee roles can lead to disengagement and decreased productivity.

**Recommended Actions:**
- **Regular Updates:** Hold regular meetings and updates to communicate company goals, progress, and any changes in strategy.
- **Goal Alignment:** Ensure that individual and team objectives are aligned with the overall company strategy to provide a clear sense of purpose.
- **Feedback Mechanisms:** Establish channels for employees to provide feedback and ask questions, fostering a two-way communication flow.

### Prioritization of Actions

1. **Immediate Priority: Job Security and Communication**
   - Implement transparent communication strategies and provide immediate support for job security concerns through internal mobility and reskilling initiatives.

2. **Short-term Priority: Skill Development**
   - Launch targeted upskilling and reskilling programs to address immediate skill gaps and prepare employees for technological changes.

3. **Long-term Priority: Cultural and Structural Changes**
   - Develop a continuous learning culture and establish robust feedback mechanisms to ensure ongoing alignment with company direction and employee engagement.

By addressing these priorities, the stakeholder group of employees can better navigate market changes, enhance their job security, and align with the evolving needs of the organization.
### Analysis of Market Changes Impacting Investors

#### 1. Market Changes Overview
- **Economic Fluctuations**: Recent economic indicators suggest potential volatility due to geopolitical tensions, inflationary pressures, and changing interest rates.
- **Technological Advancements**: Rapid technological innovation is disrupting traditional industries, creating both opportunities and risks.
- **Regulatory Shifts**: Increasing regulatory scrutiny in sectors like technology, finance, and energy could impact profitability and operational flexibility.

#### 2. Specific Impacts on Investors

##### A. Expect Growth
- **Opportunities**: 
  - **Emerging Markets**: Growth potential in emerging markets due to urbanization and increasing consumer spending.
  - **Tech and Green Sectors**: High growth potential in technology and renewable energy sectors driven by innovation and sustainability trends.
- **Challenges**:
  - **Market Saturation**: In mature markets, growth may be limited, requiring strategic investments in high-growth sectors.
  - **Competition**: Increased competition in high-growth sectors may compress margins.

##### B. Want Cost Control
- **Opportunities**:
  - **Automation and AI**: Adoption of automation and AI can reduce operational costs and improve efficiency.
  - **Supply Chain Optimization**: Streamlining supply chains can lead to significant cost savings.
- **Challenges**:
  - **Inflation**: Rising costs of raw materials and labor could pressure margins.
  - **Regulatory Compliance**: Compliance with new regulations may increase operational costs.

##### C. Risk Concerns
- **Opportunities**:
  - **Diversification**: Diversifying portfolios across sectors and geographies can mitigate risks.
  - **Hedging Strategies**: Utilizing financial instruments to hedge against currency and interest rate risks.
- **Challenges**:
  - **Market Volatility**: Increased volatility can impact asset valuations and investor confidence.
  - **Cybersecurity Risks**: Growing threat of cyberattacks poses significant risks to investments, especially in tech-heavy portfolios.

#### 3. Recommended Actions for Investors

##### Priority 1: Focus on Growth Opportunities
- **Action**: Allocate capital to high-growth sectors such as technology, healthcare, and renewable energy. Consider investments in emerging markets with favorable demographic trends.
- **Rationale**: These sectors and regions offer the potential for higher returns, aligning with growth expectations.

##### Priority 2: Implement Cost Control Measures
- **Action**: Encourage portfolio companies to adopt cost-saving technologies like AI and automation. Advocate for supply chain efficiencies and lean operations.
- **Rationale**: Cost control is essential to maintain profitability, especially in a high-inflation environment.

##### Priority 3: Mitigate Risks
- **Action**: Diversify investment portfolios to spread risk across different asset classes and geographies. Employ hedging strategies to protect against market volatility and currency fluctuations.
- **Rationale**: Diversification and hedging can reduce exposure to specific risks, safeguarding investments.

##### Priority 4: Stay Informed and Adaptive
- **Action**: Regularly review market trends and regulatory changes. Be prepared to adjust investment strategies in response to new information.
- **Rationale**: Staying informed allows investors to anticipate changes and adapt strategies proactively, minimizing potential negative impacts.

By focusing on these priorities and actions, investors can better navigate the current market landscape, balancing growth expectations with cost control and risk management.
### Analysis of Market Changes Impacting Suppliers

#### Introduction
Suppliers play a crucial role in the supply chain, providing essential materials and components to manufacturers and retailers. Recent market changes, including shifts in demand, supply chain disruptions, and economic fluctuations, have significant implications for suppliers. This analysis focuses on two primary concerns for suppliers: capacity constraints and price pressures.

### Impact Analysis

#### 1. Capacity Constraints

**Current Situation:**
- **Increased Demand:** Post-pandemic recovery and economic growth have led to a surge in demand across various sectors, straining supplier capacities.
- **Supply Chain Disruptions:** Global events, such as geopolitical tensions and natural disasters, have disrupted supply chains, affecting the availability of raw materials and components.
- **Labor Shortages:** A shortage of skilled labor in manufacturing and logistics sectors further exacerbates capacity issues.

**Specific Impacts:**
- **Production Delays:** Inability to meet increased demand may lead to production delays and missed delivery deadlines.
- **Loss of Business:** Persistent capacity issues could result in loss of contracts or business to more agile competitors.
- **Increased Operational Costs:** Overtime pay and expedited shipping costs to meet demand can erode profit margins.

#### 2. Price Pressures

**Current Situation:**
- **Rising Raw Material Costs:** Fluctuations in commodity prices, driven by supply chain disruptions and increased demand, are elevating raw material costs.
- **Inflation:** General inflationary trends are increasing the cost of goods and services, impacting supplier pricing strategies.
- **Competitive Pricing:** Intense competition forces suppliers to maintain competitive pricing, squeezing profit margins.

**Specific Impacts:**
- **Reduced Profit Margins:** Increased input costs without corresponding price adjustments can significantly reduce profitability.
- **Contractual Challenges:** Fixed-price contracts may become untenable if suppliers cannot pass on increased costs to customers.
- **Financial Strain:** Sustained price pressures can lead to cash flow issues and financial instability.

### Recommended Actions

#### Addressing Capacity Constraints

1. **Invest in Technology and Automation:**
   - **Priority:** High
   - **Action:** Implement advanced manufacturing technologies and automation to enhance production efficiency and capacity.
   - **Benefit:** Increases output, reduces reliance on labor, and improves scalability.

2. **Diversify Supply Sources:**
   - **Priority:** Medium
   - **Action:** Establish relationships with multiple suppliers to mitigate risks associated with supply chain disruptions.
   - **Benefit:** Ensures a steady supply of raw materials and components.

3. **Enhance Workforce Management:**
   - **Priority:** Medium
   - **Action:** Invest in training and development programs to upskill the workforce and attract new talent.
   - **Benefit:** Addresses labor shortages and improves operational efficiency.

#### Mitigating Price Pressures

1. **Implement Dynamic Pricing Strategies:**
   - **Priority:** High
   - **Action:** Adopt flexible pricing models that allow for adjustments based on market conditions and input costs.
   - **Benefit:** Protects profit margins and maintains competitiveness.

2. **Negotiate Long-term Contracts:**
   - **Priority:** Medium
   - **Action:** Secure long-term contracts with key customers and suppliers to stabilize prices and ensure consistent demand.
   - **Benefit:** Provides financial predictability and reduces exposure to market volatility.

3. **Optimize Cost Structures:**
   - **Priority:** Medium
   - **Action:** Conduct a thorough review of operational costs and identify areas for cost reduction, such as energy efficiency and waste minimization.
   - **Benefit:** Improves overall profitability and resilience against price pressures.

### Conclusion

Suppliers must proactively address capacity constraints and price pressures to remain competitive and sustainable in a rapidly changing market. By investing in technology, diversifying supply sources, and adopting dynamic pricing strategies, suppliers can enhance their operational capabilities and financial stability. Prioritizing these actions will enable suppliers to navigate current challenges and capitalize on emerging opportunities.
```
</details>


### Dynamic routing based on LLM output
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](routing/service.py)

Route the execution to different tools based on the LLM's output. Routing decisions are persisted and can be retried.

Send an HTTP request to the service by running the [client](routing/client.py):

```shell
uv run routing_client
```

In the UI, you can see how the LLM decides to forward the request to the technical support team, and how the response is processed:

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/routing.png" alt="Dynamic routing based on LLM output - UI"/>

<details>
<summary>View Output</summary>

```text
Processing support tickets...


Ticket 1:
----------------------------------------
Subject: Can't access my account
    Message: Hi, I've been trying to log in for the past hour but keep getting an 'invalid password' error. 
    I'm sure I'm using the right password. Can you help me regain access? This is urgent as I need to 
    submit a report by end of day.
    - John

Response:
----------------------------------------
Account Support Response:

Dear John,

Thank you for reaching out regarding your account access issue. Your account security is our top priority, and we are here to assist you in regaining access as swiftly and securely as possible.

1. **Account Verification**: To begin the recovery process, please verify your identity by providing the following information:
   - The email address associated with your account.
   - The last successful login date, if known.
   - Any recent changes made to your account settings.

2. **Password Reset**: If you are unable to recall your password, we recommend initiating a password reset. Please follow these steps:
   - Go to the login page and click on "Forgot Password?"
   - Enter your registered email address and follow the instructions sent to your email to reset your password.
   - Ensure your new password is strong, using a mix of letters, numbers, and symbols.

3. **Security Tips**: 
   - Avoid using the same password across multiple accounts.
   - Enable two-factor authentication (2FA) for an added layer of security.
   - Regularly update your passwords and review your account activity for any unauthorized access.

4. **Resolution Time**: Once you have completed the password reset, you should be able to access your account immediately. If you encounter any further issues, please contact our support team directly for additional assistance. We aim to resolve all account access issues within 24 hours.

Please let us know if you need further assistance or if there are any other concerns regarding your account security.

Best regards,

[Your Company’s Account Security Team]

Ticket 2:
----------------------------------------
Subject: Unexpected charge on my card
    Message: Hello, I just noticed a charge of $49.99 on my credit card from your company, but I thought
    I was on the $29.99 plan. Can you explain this charge and adjust it if it's a mistake?
    Thanks,
    Sarah

Response:
----------------------------------------
Billing Support Response:

Hello Sarah,

Thank you for reaching out to us regarding the unexpected charge on your credit card. I understand your concern about the $49.99 charge when you were expecting to be billed $29.99.

Upon reviewing your account, it appears that the charge of $49.99 is due to an upgrade to a higher-tier plan that was activated on your account. This plan includes additional features and benefits that are not available in the $29.99 plan. It's possible that this upgrade was selected inadvertently.

To resolve this issue, here are the next steps:
1. If you did not intend to upgrade, please confirm this by replying to this message, and we will revert your account back to the $29.99 plan.
2. Once confirmed, we will process a refund for the difference of $20.00. This refund will be initiated within 2 business days and should reflect on your credit card statement within 5-7 business days, depending on your bank's processing time.

If you wish to continue with the upgraded plan, no further action is needed, and you will continue to enjoy the additional features.

For your convenience, we accept payments via credit card, debit card, and PayPal. Please let us know if you have any further questions or need additional assistance.

Thank you for your understanding and patience.

Best regards,
[Your Name]
Billing Support Specialist

Ticket 3:
----------------------------------------
Subject: How to export data?
    Message: I need to export all my project data to Excel. I've looked through the docs but can't
    figure out how to do a bulk export. Is this possible? If so, could you walk me through the steps?
    Best regards,
    Mike

Response:
----------------------------------------
Technical Support Response:

1. **Verify System Requirements:**
   - Ensure you have the latest version of the software installed.
   - Confirm that Microsoft Excel (version 2010 or later) is installed on your system.

2. **Access the Export Function:**
   - Open the application where your project data is stored.
   - Navigate to the "Projects" section or the specific area where your data is located.

3. **Select Data for Export:**
   - If the application allows, select all projects or the specific projects you wish to export.
   - Look for an "Export" or "Export Data" option, typically found in the toolbar or under a "File" or "Options" menu.

4. **Choose Export Format:**
   - When prompted, select "Excel" or ".xlsx" as the export format.
   - If the option is available, choose "Bulk Export" to export all project data at once.

5. **Initiate Export:**
   - Click on the "Export" button to start the process.
   - Choose a destination folder on your computer where the Excel file will be saved.

6. **Verify Exported Data:**
   - Once the export is complete, navigate to the chosen destination folder.
   - Open the Excel file to ensure all project data has been exported correctly.

7. **Common Workarounds:**
   - If the bulk export option is not available, consider exporting projects individually and then merging them in Excel.
   - If you encounter any errors, try restarting the application and repeating the steps.

8. **Escalation Path:**
   - If you continue to experience issues or if the export feature is not functioning as expected, please contact our technical support team at [support@example.com](mailto:support@example.com) or call us at 1-800-555-0199 for further assistance.

Please let us know if you need any additional help.

```

</details>

### Orchestrator-worker pattern
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](orchestrator_workers/service.py)

A resilient orchestration workflow in which a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and analyzes their results.

Send an HTTP request to the service by running the [client](orchestrator_workers/client.py):

```shell
uv run orchestrator_client
```

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/orchestrator.png" alt="Orchestrator-worker pattern - UI"/>

<details>
<summary>View output</summary>

```
{'analysis': '\n'
             'The task involves creating a product description for a new '
             "eco-friendly water bottle. The goal is to convey the product's "
             'features, benefits, and unique selling points to potential '
             'customers. Variations in the approach can cater to different '
             'audiences and marketing channels. A formal approach would be '
             'valuable for technical specifications and professional settings, '
             'while a conversational approach would appeal to a broader '
             'audience by creating an emotional connection and highlighting '
             'lifestyle benefits. Each approach serves to inform and persuade '
             'potential buyers, but through different tones and focuses.\n',
 'worker_results': [{'description': '>Write a precise, technical version that '
                                    'emphasizes specifications such as '
                                    'materials used, capacity, dimensions, and '
                                    'environmental impact. This approach is '
                                    'suitable for product listings on '
                                    'e-commerce platforms or technical '
                                    'brochures where detailed information is '
                                    'prioritized.<',
                     'result': '\n'
                               'Introducing the EcoPure Hydration Vessel, a '
                               'state-of-the-art eco-friendly water bottle '
                               'designed for the environmentally conscious '
                               'consumer. Crafted from 100% recycled stainless '
                               'steel, this water bottle exemplifies '
                               'sustainability without compromising on '
                               'durability or performance. The EcoPure '
                               'Hydration Vessel boasts a generous capacity of '
                               '750 milliliters (25.4 ounces), making it ideal '
                               'for daily hydration needs.\n'
                               '\n'
                               'The dimensions of the bottle are meticulously '
                               'engineered for convenience and portability, '
                               'measuring 25 centimeters in height with a '
                               'diameter of 7 centimeters, and a weight of '
                               'just 300 grams. Its sleek, cylindrical design '
                               'ensures it fits comfortably in standard cup '
                               'holders and backpack pockets, while the '
                               'double-walled vacuum insulation technology '
                               'maintains beverage temperature for up to 24 '
                               'hours.\n'
                               '\n'
                               'The EcoPure Hydration Vessel is equipped with '
                               'a BPA-free, leak-proof cap, ensuring a secure '
                               'seal and preventing spills. The cap is also '
                               'designed with an ergonomic handle for easy '
                               "carrying. The bottle's exterior features a "
                               'powder-coated finish, providing a non-slip '
                               'grip and resistance to scratches and wear.\n'
                               '\n'
                               'In terms of environmental impact, the EcoPure '
                               'Hydration Vessel is a testament to sustainable '
                               'manufacturing practices. By utilizing recycled '
                               'materials, the production process '
                               'significantly reduces carbon emissions and '
                               'energy consumption compared to conventional '
                               'methods. Additionally, this water bottle is '
                               'fully recyclable at the end of its lifecycle, '
                               'contributing to a circular economy and '
                               'minimizing waste.\n'
                               '\n'
                               'Choose the EcoPure Hydration Vessel for a '
                               'reliable, eco-conscious hydration solution '
                               'that aligns with your commitment to preserving '
                               "our planet's resources.\n",
                     'type': 'formal'},
                    {'description': '>Write an engaging, friendly version that '
                                    'connects with readers by focusing on the '
                                    'lifestyle benefits, ease of use, and the '
                                    'positive impact of choosing an '
                                    'eco-friendly product. This approach is '
                                    'ideal for social media posts, blogs, or '
                                    'marketing emails where creating a '
                                    'personal connection and inspiring action '
                                    'is key.<',
                     'result': '\n'
                               'Hey there, hydration heroes! 🌿💧\n'
                               '\n'
                               'Meet your new favorite sidekick in the quest '
                               'for a healthier planet and a healthier you—the '
                               'EcoSip Water Bottle! Imagine a world where '
                               'staying hydrated is not just a personal win '
                               "but a victory for Mother Earth too. That's "
                               'exactly what EcoSip is all about.\n'
                               '\n'
                               'Crafted from sustainable materials, this '
                               'bottle is as kind to the planet as it is to '
                               "your lifestyle. It's lightweight, durable, and "
                               'designed to fit seamlessly into your daily '
                               "routine. Whether you're hitting the gym, "
                               'heading to the office, or exploring the great '
                               'outdoors, EcoSip is your trusty companion, '
                               'keeping your drinks refreshingly cool or '
                               'soothingly warm for hours.\n'
                               '\n'
                               "But here's the best part: every sip you take "
                               'is a step towards reducing single-use plastic '
                               "waste. Feel good knowing that you're making a "
                               'positive impact with every refill. Plus, with '
                               'its sleek design and vibrant colors, EcoSip is '
                               "not just a bottle—it's a statement. A "
                               'statement that says, "I care about the planet, '
                               'and I care about myself."\n'
                               '\n'
                               'So, why not make the switch today? Join the '
                               'EcoSip movement and be part of a community '
                               "that's committed to making a difference, one "
                               "bottle at a time. Let's raise our EcoSips and "
                               'toast to a greener, more sustainable future. '
                               'Cheers to that! 🌎✨\n'
                               '\n'
                               '#EcoSip #HydrateResponsibly #PlanetFriendly\n',
                     'type': 'conversational'}]}
```

</details>

### Evaluator-optimizer pattern
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](evaluator_optimizer/service.py)

Let the LLM generate a response, and ask another LLM to evaluate the response, and let them iterate on it.

Send an HTTP request to the service by running the [client](evaluator_optimizer/client.py):

```shell
uv run evaluator_client
```

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/evaluator.png" alt="Evaluator-optimizer pattern - UI"/>

<details>
<summary>View Output</summary>

```text
=== GENERATION START ===
Thoughts:

The task requires implementing a stack with three operations: push, pop, and getMin, all in constant time complexity, O(1). A common approach to achieve this is by using two stacks: one for storing the actual stack elements and another for keeping track of the minimum elements. This ensures that each operation can be performed in constant time. There is no feedback to consider, so I will proceed with this approach.


Generated:

\`\`\`python
class MinStack:
    def __init__(self):
        self.stack = []
        self.min_stack = []

    def push(self, x):
        self.stack.append(x)
        # Push the new minimum onto the min_stack
        if not self.min_stack or x <= self.min_stack[-1]:
            self.min_stack.append(x)

    def pop(self):
        if self.stack:
            top = self.stack.pop()
            # If the popped element is the minimum, pop it from the min_stack as well
            if top == self.min_stack[-1]:
                self.min_stack.pop()

    def getMin(self):
        # The current minimum is the top of the min_stack
        if self.min_stack:
            return self.min_stack[-1]
        return None
\`\`\`

=== GENERATION END ===

=== EVALUATION START ===
Status: PASS
Feedback: 
The code correctly implements a stack with push, pop, and getMin operations, all in O(1) time complexity. The use of an auxiliary stack (`min_stack`) to keep track of the minimum values ensures that the getMin operation is efficient. The code follows good style and best practices, with clear method names and appropriate use of data structures. No improvements are necessary.

=== EVALUATION END ===


=== GENERATION START ===
Thoughts:

The task requires implementing a stack that supports push, pop, and getMin operations, all in constant time complexity, O(1). A common approach to achieve this is by using two stacks: one for storing the actual stack elements and another for keeping track of the minimum elements. This ensures that each operation can be performed in constant time. There is no feedback from previous generations, so I will proceed with this approach.


Generated:

class MinStack:
    def __init__(self):
        self.stack = []
        self.min_stack = []

    def push(self, x):
        self.stack.append(x)
        # If the min_stack is empty or the current element is smaller or equal to the top of the min_stack, push it onto the min_stack
        if not self.min_stack or x <= self.min_stack[-1]:
            self.min_stack.append(x)

    def pop(self):
        if self.stack:
            top = self.stack.pop()
            # If the popped element is the same as the top of the min_stack, pop it from the min_stack as well
            if top == self.min_stack[-1]:
                self.min_stack.pop()

    def getMin(self):
        # The top of the min_stack is the minimum element
        if self.min_stack:
            return self.min_stack[-1]
        return None

=== GENERATION END ===

=== EVALUATION START ===
Status: PASS
Feedback: 
The code correctly implements a stack with push, pop, and getMin operations, all in O(1) time complexity. The use of an auxiliary stack (min_stack) to keep track of the minimum values ensures that getMin can be performed in constant time. The code follows good style and best practices, with clear and concise comments explaining the logic. There are no improvements needed.

=== EVALUATION END ===

```

</details>

### Human-in-the-loop pattern

An LLM generates a response, and then a human can review and approve the response before the LLM continues with the next step.

#### Option 1: `run_with_promise` handler
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](human_in_the_loop/service.py)

This handler gathers human feedback by blocking the generation-evaluation loop on a Promise that gets resolved with human feedback.

This is a **Durable Promise**, meaning that the promise can be recovered across processes and time. The Promise is persisted inside Restate. 

Test this out by killing the service halfway through or restarting the Restate Server. You will notice that Restate will still be able to resolve the promise and invoke the handler again.

```shell
curl localhost:8080/HumanInTheLoopService/giselle/run_with_promise \
    --json '"Write a poem about Durable Execution"'
```

Then use the printed curl command to incorporate external feedback. And supply `PASS` as feedback to accept the solution.

You can see how the feedback gets incorporated in the Invocations tab in the Restate UI (`http://localhost:9070`):

<img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/human_in_the_loop.png" alt="Human-in-the-loop pattern - UI"/>

<details>
<summary>View Output</summary>

```text
=== GENERATION START ===
Generated:
**Durable Execution**

In the realm where code and dreams entwine,  
Lies a concept, steadfast through the sands of time.  
Durable execution, a beacon bright,  
Guiding processes through the endless night.  

Born from the chaos of fleeting tasks,  
Where transient whispers in silence bask,  
It stands as a sentinel, firm and true,  
Ensuring each promise is brought into view.  

Like a river that carves its destined course,  
It flows with purpose, a relentless force.  
Through trials and errors, it weaves its thread,  
Binding the fragments where others have fled.  

In the dance of logic, it finds its grace,  
A symphony of order in digital space.  
With every heartbeat, it charts its way,  
Turning ephemeral night into enduring day.  

Resilient as the oak, it bends, not breaks,  
Through storms of data, it calmly wakes.  
A guardian of progress, it holds the line,  
In the tapestry of code, it does entwine.  

So let us honor this silent knight,  
In the world of zeros, it brings the light.  
For in its embrace, we find our peace,  
A promise of continuity that will never cease.  
=== GENERATION END ===


=== HUMAN FEEDBACK REQUIRED ===
Answer 'PASS' to accept the solution.

 Send feedback via:

 curl http://localhost:8080/restate/awakeables/sign_1b_yMYkXmOxYBltiXV3_RRSWrVXw8R6qhAAAAEQ/resolve --json '"Your feedback..."'
```

</details>


#### Option 2: `run` handler
[<img src="https://raw.githubusercontent.com/restatedev/img/refs/heads/main/show-code.svg">](human_in_the_loop/service.py)

Repeatedly invoke the handler with feedback until the response is satisfactory.

This is useful when the person providing feedback is the same as the one generating the response.

Restate keeps the state 

Use the UI playground to test the human-in-the-loop.
1. Go to the Restate UI at `http://localhost:9070`
2. Click on the `HumanInTheLoopService` and then on the `Playground` button.
3. Select the `run` handler and send it a message. For example:

   <img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/human_in_the_loop.png" alt="Human-in-the-loop" width="900px"/>

4. You can then provide feedback on the response and send it back to the handler.

   <img src="https://raw.githubusercontent.com/restatedev/ai-examples/refs/heads/main/doc/img/patterns/human_in_the_loop_2.png" alt="Human-in-the-loop" width="900px"/>


Alternatively, you can use `curl`:
```shell
curl localhost:8080/HumanInTheLoopService/giselle/run --json '"Write a poem about Durable Execution"'
```

And repeatedly do the same to provide feedback.