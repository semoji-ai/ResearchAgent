from fastapi import APIRouter, Request
import json

router = APIRouter(
    prefix="/bot",
    tags=["Messenger Bot"]
)

@router.post("/slack/webhook")
async def slack_webhook(request: Request):
    """
    Webhook to receive messages from Slack.
    Uses Claude API to parse natural language schedules.
    """
    data = await request.json()

    # Example logic:
    # 1. Catch `text` from Slack event
    # 2. If text contains scheduling intent, parse date/time with LLM
    # 3. Use Google Calendar API to create event
    # 4. Return success message or Interactive Button payload if confirmation needed

    # Simulated parsing
    text = data.get("event", {}).get("text", "")

    if "일정 잡아줘" in text:
        return {"text": "📅 캘린더에 일정을 등록했습니다: [다음 주 금요일 오후 3시 테스트 일정]"}
    elif "삭제해줘" in text:
        # Require human-in-the-loop approval
        return {
            "text": "정말로 일정을 삭제하시겠습니까?",
            "attachments": [
                {
                    "fallback": "You are unable to choose",
                    "callback_id": "delete_event_confirm",
                    "actions": [
                        {"name": "confirm", "text": "네, 삭제합니다", "type": "button", "value": "yes", "style": "danger"},
                        {"name": "cancel", "text": "취소", "type": "button", "value": "no"}
                    ]
                }
            ]
        }

    return {"status": "ignored"}

@router.post("/chat/webhook")
async def google_chat_webhook(request: Request):
    """
    Webhook to receive messages from Google Chat.
    """
    data = await request.json()
    message = data.get("message", {}).get("text", "")

    if "일정" in message:
        return {"text": "Google Calendar와 연동하여 일정을 관리해 드립니다."}

    return {"text": "윤비서 봇입니다. 무엇을 도와드릴까요?"}
