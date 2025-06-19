import httpx

support_routes = {
    "billing": """You are a billing support specialist. Follow these guidelines:
    1. Always start with "Billing Support Response:"
    2. First acknowledge the specific billing issue
    3. Explain any charges or discrepancies clearly
    4. List concrete next steps with timeline
    5. End with payment options if relevant

    Keep responses professional but friendly.

    Input: """,
    "technical": """You are a technical support engineer. Follow these guidelines:
    1. Always start with "Technical Support Response:"
    2. List exact steps to resolve the issue
    3. Include system requirements if relevant
    4. Provide workarounds for common problems
    5. End with escalation path if needed

    Use clear, numbered steps and technical details.

    Input: """,
    "account": """You are an account security specialist. Follow these guidelines:
    1. Always start with "Account Support Response:"
    2. Prioritize account security and verification
    3. Provide clear steps for account recovery/changes
    4. Include security tips and warnings
    5. Set clear expectations for resolution time

    Maintain a serious, security-focused tone.

    Input: """,
    "product": """You are a product specialist. Follow these guidelines:
    1. Always start with "Product Support Response:"
    2. Focus on feature education and best practices
    3. Include specific examples of usage
    4. Link to relevant documentation sections
    5. Suggest related features that might help

    Be educational and encouraging in tone.

    Input: """,
}

# Test with different support tickets
tickets = [
    """Subject: Can't access my account
    Message: Hi, I've been trying to log in for the past hour but keep getting an 'invalid password' error. 
    I'm sure I'm using the right password. Can you help me regain access? This is urgent as I need to 
    submit a report by end of day.
    - John""",
    """Subject: Unexpected charge on my card
    Message: Hello, I just noticed a charge of $49.99 on my credit card from your company, but I thought
    I was on the $29.99 plan. Can you explain this charge and adjust it if it's a mistake?
    Thanks,
    Sarah""",
    """Subject: How to export data?
    Message: I need to export all my project data to Excel. I've looked through the docs but can't
    figure out how to do a bulk export. Is this possible? If so, could you walk me through the steps?
    Best regards,
    Mike""",
]


def main():
    print("Processing support tickets...\n")
    for i, ticket in enumerate(tickets, 1):
        print(f"\nTicket {i}:")
        print("-" * 40)
        print(ticket)
        print("\nResponse:")
        print("-" * 40)

        data = {"input": ticket, "routes": support_routes}

        r = httpx.post(
            "http://localhost:8080/RoutingService/route",
            json=data,
            timeout=60,
        )
        r.raise_for_status()

        print(r.json())


if __name__ == "__main__":
    main()

"""
Example output:

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
"""
