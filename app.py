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
def load_adaptive_card(file_name):
    with open(f"json/{file_name}.json", "r", encoding="utf-8") as f:
        return json.load(f)

ADAPTIVE_CARD = load_adaptive_card("hiring_msg")



# -------- Bot Class --------
class HelloCardBot:
    async def on_message_activity(self, turn_context: TurnContext):
        activity = turn_context.activity

        # Handle Adaptive Card button clicks (Action.Submit → activity.value)
        submitted = getattr(activity, "value", None)
        if submitted and isinstance(submitted, dict) and "action" in submitted:
            action = submitted["action"]

            if action == "view_requirements":
                card_attachment = Attachment(
                content_type="application/vnd.microsoft.card.adaptive",
                content=load_adaptive_card("requirement")
                )

                reply = Activity(
                type=ActivityTypes.message,
                attachments=[card_attachment]
                )

                await turn_context.send_activity(reply)
                return

            if action == "slot_suggestion":
                # await turn_context.send_activity(MessageFactory.text("Creating slot suggestions for you based on your calendar"))

                # await turn_context.send_activity(Activity(type=ActivityTypes.typing))

                # # await turn_context.adapter(turn_context)
                
                # await asyncio.sleep(3)

                card_attachment = Attachment(
                content_type="application/vnd.microsoft.card.adaptive",
                content=load_adaptive_card("slot_suggestion")
                )

                reply = Activity(
                type=ActivityTypes.message,
                attachments=[card_attachment]
                )

                await turn_context.send_activity((reply))
                return
            
            if action == "decline":
                await turn_context.send_activity(
                    "Thank you for your response!\n"
                    "You have been marked unavailable for this interview.\n"
                    "We’ll reach out for future rounds.\n"
                )
                return

            if action == "confirm":
                submitted_slots_raw = submitted.get("selectedSlot")  # when multi-select, AdaptiveCards sends a comma-separated string
                manual_date = submitted.get("manualDate")
                manual_time = submitted.get("manualTime")

                # Normalize selected slots into a list of tuples (id, iso_start)
                parsed_slots = []

                if submitted_slots_raw:
                    # Adaptive Cards sends multi-select as comma-separated string.
                    # Example item format expected: "slot-1|2025-02-15T14:00"
                    for part in submitted_slots_raw.split(","):
                        part = part.strip()
                        if not part:
                            continue
                        if "|" in part:
                            sid, iso = part.split("|", 1)
                        else:
                            # fallback if value was just iso without id
                            sid, iso = ("", part)
                        parsed_slots.append((sid, iso))

                # If manual date/time provided, append it as a "manual-<n>" id
                if manual_date and manual_time:
                    # Join into ISO-like string accepted by datetime.fromisoformat
                    manual_iso = f"{manual_date}T{manual_time}"
                    # Make a unique manual id based on count
                    manual = f"Slot 4 "
                    parsed_slots.append((manual, manual_iso))

                # If nothing selected or entered
                if not parsed_slots:
                    await turn_context.send_activity("Please select at least one slot or enter a manual date and time.")
                    return

                # Build formatted lines for the single confirmation message
                formatted_lines = []
                for sid, iso in parsed_slots:
                    try:
                        start_dt = datetime.fromisoformat(iso)
                    except Exception as e:
                        # If parsing fails, skip gracefully and record the raw value
                        formatted_lines.append(f"- {sid or ''} : (invalid datetime: {iso})")
                        continue

                    # compute end time (+45 minutes)
                    end_dt = start_dt + timedelta(minutes=45)

                    # format date and times
                    date_str = start_dt.strftime("%a, %d %b")
                    start_str = start_dt.strftime("%I:%M %p").lstrip("0")
                    end_str = end_dt.strftime("%I:%M %p").lstrip("0")

                    if sid:
                        formatted_lines.append(f"- {sid} : {date_str} - {start_str} to {end_str}")
                    else:
                        formatted_lines.append(f"- {date_str} - {start_str} to {end_str}")
                
                #add data in data.txt
                with open("./data.txt","w") as f:
                    f.writelines("\n".join(formatted_lines))
                # Build final message (single message)
                message = (
                    "Thanks! I have recorded your availability."
                    "\n\n"
                    "You will receive an email invite with all relevant details to block this time in your calendar. "
                    "A reminder will be sent 2 hours before your scheduled interview.\n\n"
                    "Selected slot(s):\n"
                    + "\n".join(formatted_lines)
                )

                await turn_context.send_activity(message)
                return
            
                

            
            if action == "provide_availability":
                card_attachment = Attachment(
                content_type="application/vnd.microsoft.card.adaptive",
                content=load_adaptive_card("provide_availability")
                )

                reply = Activity(
                type=ActivityTypes.message,
                attachments=[card_attachment]
                )

                await turn_context.send_activity(reply)
                return

        # Fallback text handling
        user_text = activity.text or ""
        await turn_context.send_activity(f"Hello World — you said: {user_text}")

    async def on_conversation_update_activity(self, members_added,turn_context: TurnContext):
        card_attachment = Attachment(
            content_type="application/vnd.microsoft.card.adaptive",
            content=ADAPTIVE_CARD
        )

        reply = Activity(
            type=ActivityTypes.message,
            attachments=[card_attachment]
        )

        await turn_context.send_activity(reply)


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
    app.router.add_post("/api/messages", messages)

    print("Bot running at: http://localhost:3978/api/interviewer")
    web.run_app(app, host="0.0.0.0", port=3978)
