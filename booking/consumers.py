import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import sync_to_async
from .utils import get_remaining_seats


class BookingConsumer(AsyncJsonWebsocketConsumer):
    group_name = 'booking_updates'

    async def connect(self):
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # send initial remaining count
        try:
            remaining = await sync_to_async(get_remaining_seats)()
        except Exception:
            remaining = None
        await self.send_json({
            'event': 'COUNT_UPDATE',
            'remaining': remaining,
        })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # No client messages expected for this consumer; ignore.
        return

    async def count_update(self, event):
        # handler for type "count.update"
        remaining = event.get('remaining')
        await self.send_json({
            'event': 'COUNT_UPDATE',
            'remaining': remaining,
        })
