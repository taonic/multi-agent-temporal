import os
import re
import asyncio

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from temporal.agent import Agent, Runner

from .tools import get_slack_channels, search_slack, get_thread_messages
from .sys_prompt import get_system_prompt


# Stream agent thoughts back to slack
async def _poll_thoughts_to_slack(agent, say, watermark=0):
    try:
        while True:
            thoughts = await agent.thoughts(watermark=watermark)
            if thoughts:
                for line in thoughts:
                    await say(f"🧠 {line}")
                watermark += len(thoughts)
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        pass

async def main():
    # Slack credentials
    bot_token  = os.environ["SLACK_BOT_TOKEN"]
    app_token  = os.environ["SLACK_APP_TOKEN"]

    # Initialise the LLM-powered agent
    agent = Agent(
        name="Slack Research Agent",
        model_name="models/gemini-2.5-pro-preview-05-06",
        instruction=get_system_prompt(),
        functions=[get_slack_channels, search_slack, get_thread_messages],
    )

    async with Runner(app_name="slack_agent", agent=agent) as runner:
        slack_app = AsyncApp(token=bot_token)

        # Handle mentions
        @slack_app.event("app_mention")
        async def handle_app_mention(body, say):
            """
            Whenever the bot is mentioned, strip the mention from the text,
            send it to the agent, and post the reply back to Slack.
            """
            raw_text = body["event"]["text"]
            # Remove the bot mention (e.g. "<@U123ABC> hello" → "hello")
            user_text = re.sub(r"<@[^>]+>", "", raw_text).strip()
            if not user_text:
                await say("🤖 Please include a question after mentioning me.")
                return

            await say("🤔 Thinking…")
            thoughts_task = asyncio.create_task(_poll_thoughts_to_slack(agent, say))

            try:
                response = await runner.prompt(user_text)
                await say(f"🤖 {response}")
            finally:
                thoughts_task.cancel()

        # Handle direct messages
        @slack_app.event("message")           
        async def handle_dm(event, say):
            print(event)
            if event.get("channel_type") != "im":      
                return
            if event.get("subtype") or event.get("bot_id"):
                return

            text = (event.get("text") or "").strip()
            if not text:
                return

            await say("🤔 Thinking…")
            poll = asyncio.create_task(_poll_thoughts_to_slack(agent, say))
            try:
                reply = await runner.prompt(text)
                await say(f"🤖 {reply}")
            finally:
                poll.cancel()

        # Websocket listener
        handler = AsyncSocketModeHandler(slack_app, app_token)
        await handler.start_async()       # blocks forever (Ctrl-C to quit)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Goodbye!")