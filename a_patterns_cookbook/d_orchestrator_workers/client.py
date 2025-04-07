from pprint import pprint

import httpx

ORCHESTRATOR_PROMPT = """
Analyze this task and break it down into 2-3 distinct approaches:

Task: {task}

Return your response in this format:

<analysis>
Explain your understanding of the task and which variations would be valuable.
Focus on how each approach serves different aspects of the task.
</analysis>

<tasks>
    <task>
    <type>formal</type>
    <description>Write a precise, technical version that emphasizes specifications</description>
    </task>
    <task>
    <type>conversational</type>
    <description>Write an engaging, friendly version that connects with readers</description>
    </task>
</tasks>
"""

WORKER_PROMPT = """
Generate content based on:
Task: {original_task}
Style: {task_type}
Guidelines: {task_description}

Return your response in this format:

<response>
Your content here, maintaining the specified style and fully addressing requirements.
</response>
"""

data = {
    "orchestrator_prompt": ORCHESTRATOR_PROMPT,
    "worker_prompt": WORKER_PROMPT,
    "task": "Write a product description for a new eco-friendly water bottle",
    "llm_context": {
        "target_audience": "environmentally conscious millenials",
        "key_features": ["plastic-free", "insulated", "lifetime warranty"]
    }
}

headers = {"Content-Type": "application/json", "Accept": "application/json"}

r = httpx.post(
    "http://localhost:8080/FlexibleOrchestrator/process",
    json=data,
    headers=headers,
    timeout=300,
)

output_json = r.json()
pprint(output_json)

"""
Example output:

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
"""