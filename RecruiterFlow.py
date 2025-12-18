import os
import json
from aiohttp import web
from datetime import datetime, timedelta
import asyncio

from botbuilder.core import (
    BotFrameworkAdapterSettings,
    BotFrameworkAdapter,
    TurnContext,
    MessageFactory
)

from botbuilder.schema import Activity, ActivityTypes, Attachment


# -------- Load Adaptive Card JSON from file --------
# def load_adaptive_card(file_name):
#     with open(f"json/{file_name}.json", "r", encoding="utf-8") as f:
#         return json.load(f)

# ADAPTIVE_CARD = load_adaptive_card("hiring_msg")



# -------- Bot Class --------
class HelloCardBot:
    async def on_message_activity(self, turn_context: TurnContext):
        activity = turn_context.activity

        # Handle Adaptive Card button clicks (Action.Submit → activity.value)
        submitted = getattr(activity, "value", None)
        if submitted and isinstance(submitted, dict) and "action" in submitted:
            action = submitted["action"]
        # Fallback text handling
        user_text = activity.text or ""
        if "update" in user_text or "onboarding" in user_text or "interview" in user_text:
            with open("./data.txt","r") as f:
                    interview_data = f.readlines()
            if not interview_data:
                await turn_context.send_activity("No update for now. Kindly wait for some time.")
                return
            if interview_data:
                message = (
                        "Hey! Here is the slot selected by Aman."
                        "\n\n"
                        "Selected slot(s):\n"
                        + "\n".join(interview_data)
                    )
                await turn_context.send_activity(message)
                return
        else:
            await turn_context.send_activity("Invalid input")
            return
    # async def on_conversation_update_activity(self, members_added,turn_context: TurnContext):
    #     card_attachment = Attachment(
    #         content_type="application/vnd.microsoft.card.adaptive",
    #         content=ADAPTIVE_CARD
    #     )

    #     reply = Activity(
    #         type=ActivityTypes.message,
    #         attachments=[card_attachment]
    #     )

    #     await turn_context.send_activity(reply)


# -------- Adapter Setup --------
APP_ID = os.getenv("MicrosoftAppId", "")
APP_PASSWORD = os.getenv("MicrosoftAppPassword", "")

adapter_settings = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
adapter = BotFrameworkAdapter(adapter_settings)

bot = HelloCardBot()


# -------- aiohttp handler for /api/messages --------
async def messages(req: web.Request) -> web.Response:
    try:
        body = await req.json()
    except:
        return web.Response(status=400, text="Invalid JSON")

    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    async def aux_func(turn_context: TurnContext):
        atype = turn_context.activity.type

        if atype == ActivityTypes.conversation_update:
            members_added = turn_context.activity.members_added
            await bot.on_conversation_update_activity(members_added, turn_context)

        elif atype == ActivityTypes.message:
            await bot.on_message_activity(turn_context)

    try:
        await adapter.process_activity(activity, auth_header, aux_func)
        return web.Response(status=201)
    except Exception as e:
        print("Exception:", e)
        return web.Response(status=500, text="Error processing request")


# -------- Run the Web Server --------
if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("/api/recruiter", messages)

    print("Bot running at: http://localhost:3978/api/recruiter")
    web.run_app(app, host="0.0.0.0", port=3978)
