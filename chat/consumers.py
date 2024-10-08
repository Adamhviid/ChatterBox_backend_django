import json
from channels.generic.websocket import AsyncWebsocketConsumer
from mongoengine import connect, Document, StringField, DateTimeField
import datetime
import uuid
import os
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
connect(db="chatterbox", host=MONGODB_URI)


class Users(Document):
    userId = StringField(required=True, unique=True)
    ip = StringField(required=True)
    connectedAt = DateTimeField(
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    meta = {"collection": "users"}


class Messages(Document):
    userId = StringField(required=True)
    message = StringField(required=True)
    sentAt = DateTimeField(default=lambda: datetime.datetime.now(datetime.timezone.utc))

    meta = {"collection": "messages"}


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.userId = str(uuid.uuid4()).split("-")[0]
        self.ip = self.scope["client"][0]
        self.room_group_name = "chat_group"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        try:
            existing_user = Users.objects(ip=self.ip).first()
            if not existing_user:
                Users(userId=self.userId, ip=self.ip).save()
                print(f"Inserted document for user {self.userId} with IP {self.ip}")
            else:
                self.userId = existing_user.userId
                print(
                    f"User with IP {self.ip} already exists with userId {self.userId}"
                )
        except Exception as e:
            print(f"Error during user lookup or insertion: {e}")

        try:
            last_messages = Messages.objects.order_by("-sentAt")[:25]
            messages_to_send = [
                {
                    "message": msg.message,
                    "userId": msg.userId,
                    "sentAt": msg.sentAt.isoformat(),
                }
                for msg in last_messages
            ]
            await self.send(
                text_data=json.dumps(
                    {"type": "load_messages", "messages": messages_to_send}
                )
            )
        except Exception as e:
            print(f"Error loading messages from database: {e}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            if not text_data:
                return
            data = json.loads(text_data)
            message = data.get("message")
            userId = data.get("userId")

            # Broadcast message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "userId": userId,
                },
            )
        except Exception as e:
            print(f"Error processing received message: {e}")

    async def chat_message(self, event):
        message = event["message"]
        userId = event["userId"]

        # Send message to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "message": message,
                    "userId": userId,
                }
            )
        )
