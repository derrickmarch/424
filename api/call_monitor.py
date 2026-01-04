"""
Real-time call monitoring API endpoints.
Provides live updates on ongoing calls with detailed logging.
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from database import get_db
from typing import List, Dict
import structlog
import json
from datetime import datetime

logger = structlog.get_logger()

router = APIRouter()

# Store active WebSocket connections for live updates
active_connections: Dict[str, List[WebSocket]] = {}


class CallMonitor:
    """Singleton class to track active calls and broadcast updates."""
    
    _instance = None
    _active_calls: Dict[str, Dict] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CallMonitor, cls).__new__(cls)
        return cls._instance
    
    def start_call(self, call_sid: str, verification_id: str, to_number: str):
        """Register a new call for monitoring."""
        self._active_calls[call_sid] = {
            'call_sid': call_sid,
            'verification_id': verification_id,
            'to_number': to_number,
            'started_at': datetime.now().isoformat(),
            'status': 'initiated',
            'events': [],
            'conversation': [],
            'api_calls': []
        }
        logger.info(f"📞 Call monitor started", call_sid=call_sid, verification_id=verification_id)
        self._broadcast_update(call_sid)
    
    def add_event(self, call_sid: str, event_type: str, message: str, data: dict = None):
        """Add an event to the call timeline."""
        if call_sid not in self._active_calls:
            return
        
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'message': message,
            'data': data or {}
        }
        
        self._active_calls[call_sid]['events'].append(event)
        logger.info(f"📝 Call event", call_sid=call_sid, event_type=event_type, message=message)
        self._broadcast_update(call_sid)
    
    def add_conversation(self, call_sid: str, speaker: str, text: str):
        """Add a conversation entry (AI or Human)."""
        if call_sid not in self._active_calls:
            return
        
        conversation = {
            'timestamp': datetime.now().isoformat(),
            'speaker': speaker,  # 'AI' or 'Human'
            'text': text
        }
        
        self._active_calls[call_sid]['conversation'].append(conversation)
        logger.info(f"💬 Conversation", call_sid=call_sid, speaker=speaker, text=text[:50])
        self._broadcast_update(call_sid)
    
    def add_api_call(self, call_sid: str, method: str, url: str, request: dict, response: dict):
        """Log an API call (Twilio, OpenAI, etc.)."""
        if call_sid not in self._active_calls:
            return
        
        api_call = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'url': url,
            'request': request,
            'response': response
        }
        
        self._active_calls[call_sid]['api_calls'].append(api_call)
        logger.info(f"🌐 API call", call_sid=call_sid, method=method, url=url)
        self._broadcast_update(call_sid)
    
    def update_status(self, call_sid: str, status: str):
        """Update the call status."""
        if call_sid not in self._active_calls:
            return
        
        self._active_calls[call_sid]['status'] = status
        logger.info(f"📊 Call status updated", call_sid=call_sid, status=status)
        self._broadcast_update(call_sid)
    
    def end_call(self, call_sid: str, final_status: str):
        """Mark call as ended."""
        if call_sid not in self._active_calls:
            return
        
        self._active_calls[call_sid]['status'] = final_status
        self._active_calls[call_sid]['ended_at'] = datetime.now().isoformat()
        logger.info(f"☎️ Call ended", call_sid=call_sid, final_status=final_status)
        self._broadcast_update(call_sid)
    
    def get_call_data(self, call_sid: str) -> dict:
        """Get all data for a specific call."""
        return self._active_calls.get(call_sid, {})
    
    def get_active_calls(self) -> List[dict]:
        """Get all active calls."""
        return [
            call for call in self._active_calls.values()
            if call.get('status') not in ['completed', 'failed', 'cancelled']
        ]
    
    def _broadcast_update(self, call_sid: str):
        """Broadcast update to all connected WebSocket clients."""
        if call_sid in active_connections:
            call_data = self.get_call_data(call_sid)
            message = json.dumps({
                'type': 'call_update',
                'call_sid': call_sid,
                'data': call_data
            })
            
            # Send to all connected clients for this call
            disconnected = []
            from anyio import from_thread
            for connection in active_connections[call_sid]:
                try:
                    # Push update to clients without blocking the event loop
                    from_thread.run(connection.send_text, message)
                except Exception:
                    disconnected.append(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                active_connections[call_sid].remove(conn)


# Global monitor instance
call_monitor = CallMonitor()


@router.get("/active-calls")
def get_active_calls(db: Session = Depends(get_db)):
    """Get all currently active calls with full details."""
    try:
        active_calls = call_monitor.get_active_calls()
        return {
            'success': True,
            'count': len(active_calls),
            'calls': active_calls
        }
    except Exception as e:
        logger.error(f"Error getting active calls: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/call/{call_sid}")
def get_call_details(call_sid: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific call."""
    try:
        call_data = call_monitor.get_call_data(call_sid)
        
        if not call_data:
            raise HTTPException(status_code=404, detail="Call not found in monitor")
        
        return {
            'success': True,
            'call': call_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting call details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/call/{call_sid}")
async def websocket_call_monitor(websocket: WebSocket, call_sid: str):
    """
    WebSocket endpoint for real-time call monitoring.
    Sends live updates as the call progresses.
    """
    await websocket.accept()
    
    # Register this connection
    if call_sid not in active_connections:
        active_connections[call_sid] = []
    active_connections[call_sid].append(websocket)
    
    logger.info(f"🔌 WebSocket connected for call monitoring", call_sid=call_sid)
    
    try:
        # Send initial call data
        call_data = call_monitor.get_call_data(call_sid)
        await websocket.send_json({
            'type': 'initial_data',
            'call_sid': call_sid,
            'data': call_data
        })
        
        # Keep connection alive and send updates
        while True:
            # Wait for messages (ping/pong or client requests)
            data = await websocket.receive_text()
            
            # Handle client requests
            if data == 'ping':
                await websocket.send_text('pong')
            elif data == 'get_update':
                call_data = call_monitor.get_call_data(call_sid)
                await websocket.send_json({
                    'type': 'update',
                    'call_sid': call_sid,
                    'data': call_data
                })
    
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected", call_sid=call_sid)
        if call_sid in active_connections:
            active_connections[call_sid].remove(websocket)
            if not active_connections[call_sid]:
                del active_connections[call_sid]
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if call_sid in active_connections and websocket in active_connections[call_sid]:
            active_connections[call_sid].remove(websocket)


@router.get("/call-history/{verification_id}")
def get_call_history(verification_id: str, db: Session = Depends(get_db)):
    """Get all calls (active and completed) for a verification."""
    try:
        from models import CallLog, AccountVerification
        
        verification = db.query(AccountVerification).filter(
            AccountVerification.verification_id == verification_id
        ).first()
        
        if not verification:
            raise HTTPException(status_code=404, detail="Verification not found")
        
        # Get all call logs from database
        call_logs = db.query(CallLog).filter(
            CallLog.verification_id == verification.id
        ).order_by(CallLog.created_at.desc()).all()
        
        # Enrich with live data if available
        enriched_calls = []
        for log in call_logs:
            call_data = {
                'call_sid': log.twilio_call_sid,
                'status': log.call_status,
                'duration': log.call_duration,
                'from_number': log.from_number,
                'to_number': log.to_number,
                'created_at': log.created_at.isoformat() if log.created_at else None,
                'started_at': log.initiated_at.isoformat() if log.initiated_at else None,
                'ended_at': log.ended_at.isoformat() if log.ended_at else None
            }
            
            # Add live monitoring data if available
            live_data = call_monitor.get_call_data(log.twilio_call_sid)
            if live_data:
                call_data['live_events'] = live_data.get('events', [])
                call_data['conversation'] = live_data.get('conversation', [])
                call_data['api_calls'] = live_data.get('api_calls', [])
                call_data['is_active'] = live_data.get('status') not in ['completed', 'failed', 'cancelled']
            else:
                call_data['is_active'] = False
            
            enriched_calls.append(call_data)
        
        return {
            'success': True,
            'verification_id': verification_id,
            'count': len(enriched_calls),
            'calls': enriched_calls
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting call history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
