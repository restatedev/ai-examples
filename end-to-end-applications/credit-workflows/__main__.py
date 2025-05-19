import hypercorn
import asyncio
import restate

from app.chat import chat_service
from app.credit_review_workflow import credit_review_workflow
from app.account import account
from app.utils.agent_session import agent_session
from app.credit_review_agent import credit_review_agent_utils, credit_worthiness_svc


def main():
    app = restate.app(
        services=[
            chat_service,
            credit_review_workflow,
            credit_review_agent_utils,
            agent_session,
            account,
            credit_worthiness_svc,
        ]
    )

    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))


if __name__ == "__main__":
    main()
