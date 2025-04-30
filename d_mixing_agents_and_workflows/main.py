import hypercorn
import asyncio
import restate

from .chat import chat_service
from .loan_review_workflow import loan_review_workflow
from .account import account
from .utils.agent_session import agent_session
from .loan_review_agent import loan_review_agent_utils, credit_worthiness_svc

def main():
    app = restate.app(
        services=[
            chat_service,
            loan_review_workflow,
            loan_review_agent_utils,
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
