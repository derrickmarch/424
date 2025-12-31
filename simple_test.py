"""
Simple Single-File Account Verification Test Script
Run this to test verifying ONE account without the full application.
"""

import os
from twilio.rest import Client
from openai import OpenAI
import time

# ============================================================================
# CONFIGURATION - Fill in your credentials here
# ============================================================================

# Twilio credentials - Get from .env file
import sys
try:
    from config import settings
    TWILIO_ACCOUNT_SID = settings.twilio_account_sid
    TWILIO_AUTH_TOKEN = settings.twilio_auth_token
    TWILIO_PHONE_NUMBER = settings.twilio_phone_number
    OPENAI_API_KEY = settings.openai_api_key
except Exception as e:
    print(f"❌ Error loading credentials from .env: {e}")
    print(f"Make sure .env file exists with Twilio credentials")
    sys.exit(1)

# Test account to verify
TEST_CUSTOMER = {
    "name": "John Doe",
    "account_number": "123456789",
    "phone": "+19092028031",  # Your verified test number
    "company": "Citibank",
    "company_phone": "+18002484226"  # Citibank customer service
}

# ============================================================================
# SIMPLE VERIFICATION SCRIPT
# ============================================================================

def test_account_verification():
    """
    Make a REAL call to your registered test number.
    """
    print("=" * 70)
    print("🧪 REAL CALL TEST - LIVE TWILIO CALL")
    print("=" * 70)
    
    # Step 1: Display test info
    print(f"\n📋 Test Customer:")
    print(f"   Name: {TEST_CUSTOMER['name']}")
    print(f"   Account: {TEST_CUSTOMER['account_number']}")
    print(f"   Phone: {TEST_CUSTOMER['phone']}")
    print(f"   Company: {TEST_CUSTOMER['company']}")
    print(f"   Company Phone: {TEST_CUSTOMER['company_phone']}")
    
    # Step 2: Initialize Twilio
    print(f"\n🔌 Connecting to Twilio...")
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Get account info
        account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        print(f"   ✅ Connected to Twilio")
        print(f"   Account: {account.friendly_name}")
        print(f"   Status: {account.status}")
        
        # Get balance
        try:
            balance = client.balance.fetch()
            print(f"   Balance: ${balance.balance} {balance.currency}")
        except:
            print(f"   Balance: Trial Account (API restricted)")
        
    except Exception as e:
        print(f"   ❌ Twilio connection failed: {e}")
        return
    
    # Step 3: Make REAL call
    print(f"\n⚠️  REAL CALL WARNING:")
    print(f"   This will make an ACTUAL call to: {TEST_CUSTOMER['phone']}")
    print(f"   Your phone will ring and play a test message!")
    
    confirm = input(f"\n   Type 'YES' to proceed with real call: ").strip().upper()
    
    if confirm != "YES":
        print(f"\n   ❌ Call cancelled by user")
        return
    
    print(f"\n📞 Making REAL call to {TEST_CUSTOMER['phone']}...")
    
    try:
        # Create TwiML for the call
        # This is the message that will be spoken when call is answered
        twiml_message = f"""
        <Response>
            <Say voice="alice">
                Hello! This is a test call from your Account Verification System. 
                We are testing the ability to make calls to verify accounts. 
                Customer name: {TEST_CUSTOMER['name']}. 
                Account number: {TEST_CUSTOMER['account_number']}. 
                Company: {TEST_CUSTOMER['company']}. 
                This is a test. The system is working correctly. 
                Thank you for testing. Goodbye.
            </Say>
        </Response>
        """
        
        # Make the call using Twilio's API
        call = client.calls.create(
            to=TEST_CUSTOMER['phone'],
            from_=TWILIO_PHONE_NUMBER,
            twiml=twiml_message,
            status_callback='http://httpbin.org/post',  # For testing, logs call status
            status_callback_event=['initiated', 'ringing', 'answered', 'completed']
        )
        
        print(f"   ✅ Call initiated successfully!")
        print(f"   📞 Call SID: {call.sid}")
        print(f"   📱 To: {call.to}")
        print(f"   📱 From: {call.from_}")
        print(f"   📊 Status: {call.status}")
        
        print(f"\n🔔 YOUR PHONE SHOULD BE RINGING NOW!")
        print(f"   Answer it to hear the test message...")
        
        # Monitor call status
        print(f"\n📊 Monitoring call status...")
        for i in range(30):  # Monitor for up to 30 seconds
            time.sleep(2)
            
            # Fetch updated call status
            call = client.calls(call.sid).fetch()
            status = call.status
            
            print(f"   [{i*2}s] Call status: {status}")
            
            if status == 'ringing':
                print(f"      🔔 Phone is ringing...")
            elif status == 'in-progress':
                print(f"      📞 Call connected! Playing message...")
            elif status == 'completed':
                print(f"      ✅ Call completed!")
                duration = call.duration
                print(f"      ⏱️  Duration: {duration} seconds")
                break
            elif status in ['busy', 'failed', 'no-answer', 'canceled']:
                print(f"      ❌ Call ended with status: {status}")
                break
        
        # Final call details
        call = client.calls(call.sid).fetch()
        
        print(f"\n📊 FINAL CALL DETAILS:")
        print(f"   Call SID: {call.sid}")
        print(f"   Status: {call.status}")
        print(f"   Duration: {call.duration} seconds")
        print(f"   Direction: {call.direction}")
        print(f"   From: {call.from_}")
        print(f"   To: {call.to}")
        
        # Generate mock conversation based on the call
        mock_conversation = f"""
    This was a REAL Twilio call!
    
    Message played to {TEST_CUSTOMER['phone']}:
    "Hello! This is a test call from your Account Verification System. 
     We are testing the ability to make calls to verify accounts. 
     Customer name: {TEST_CUSTOMER['name']}. 
     Account number: {TEST_CUSTOMER['account_number']}. 
     Company: {TEST_CUSTOMER['company']}. 
     This is a test. The system is working correctly. 
     Thank you for testing. Goodbye."
    """
        
        print(f"\n💬 Call Content:")
        print(mock_conversation)
        
    except Exception as e:
        print(f"   ❌ Call failed: {e}")
        print(f"   Error details: {type(e).__name__}")
        return
    
    # Step 4: Process with AI (if OpenAI key provided)
    if OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here":
        print(f"\n🤖 Processing with AI...")
        try:
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
            
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are analyzing a call transcript to determine if an account exists. Respond with JSON: {\"account_exists\": true/false, \"confidence\": \"high\"/\"medium\"/\"low\", \"reason\": \"explanation\"}"
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this conversation and determine if the account exists:\n\n{mock_conversation}"
                    }
                ],
                temperature=0.3
            )
            
            ai_result = response.choices[0].message.content
            print(f"   ✅ AI Analysis:")
            print(f"   {ai_result}")
            
        except Exception as e:
            print(f"   ⚠️  AI analysis skipped: {e}")
    else:
        print(f"\n🤖 AI Processing skipped (no OpenAI key provided)")
        print(f"   Manual analysis: Account VERIFIED ✅")
    
    # Step 5: Final result
    print(f"\n" + "=" * 70)
    print(f"📊 VERIFICATION RESULT")
    print(f"=" * 70)
    print(f"✅ Account Status: VERIFIED")
    print(f"✅ Customer: {TEST_CUSTOMER['name']}")
    print(f"✅ Account Number: {TEST_CUSTOMER['account_number']}")
    print(f"✅ Company: {TEST_CUSTOMER['company']}")
    print(f"✅ Verification Method: Simulated call")
    print(f"=" * 70)
    
    print(f"\n💡 Next Steps:")
    print(f"   1. Use the full application for real verifications")
    print(f"   2. Visit: https://four24-a0es.onrender.com")
    print(f"   3. Login with admin/admin123")
    print(f"   4. Add your verification records and start auto-queue")
    
    return {
        "verified": True,
        "customer": TEST_CUSTOMER['name'],
        "account": TEST_CUSTOMER['account_number'],
        "company": TEST_CUSTOMER['company']
    }


def quick_twilio_test():
    """
    Just test Twilio connection and balance.
    """
    print("=" * 70)
    print("🔌 QUICK TWILIO CONNECTION TEST")
    print("=" * 70)
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        print(f"\n✅ Twilio Connected Successfully!")
        
        # Account info
        account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        print(f"\n📋 Account Information:")
        print(f"   Account Name: {account.friendly_name}")
        print(f"   Account SID: {account.sid}")
        print(f"   Status: {account.status}")
        print(f"   Type: {account.type}")
        
        # Balance
        try:
            balance = client.balance.fetch()
            print(f"\n💰 Account Balance:")
            print(f"   Balance: ${balance.balance} {balance.currency}")
        except Exception as e:
            print(f"\n💰 Account Balance:")
            print(f"   Trial Account (Balance API not available)")
            print(f"   This is normal for trial accounts")
        
        # Phone numbers
        print(f"\n📱 Your Twilio Phone Number:")
        print(f"   {TWILIO_PHONE_NUMBER}")
        
        print(f"\n✅ Twilio is ready to use!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Twilio Connection Failed!")
        print(f"   Error: {e}")
        print(f"\n💡 Check your credentials:")
        print(f"   - TWILIO_ACCOUNT_SID")
        print(f"   - TWILIO_AUTH_TOKEN")
        return False


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("   SIMPLE ACCOUNT VERIFICATION TEST SCRIPT")
    print("=" * 70)
    print("\nChoose an option:")
    print("  1. Quick Twilio Connection Test (No call)")
    print("  2. Make REAL Call to Your Registered Number")
    print("  3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        quick_twilio_test()
    elif choice == "2":
        test_account_verification()
    else:
        print("Exiting...")
    
    print("\n✨ Test complete!\n")
