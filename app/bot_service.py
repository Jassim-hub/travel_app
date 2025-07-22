"""
Simple AI chatbot service for handling travel inquiries.
"""
import re
from datetime import datetime


class SimpleInquiryBot:
    """Simple chatbot that handles common travel inquiries."""
    
    def __init__(self):
        # Simple keyword-based responses
        self.responses = {
            'booking': {
                'keywords': ['book', 'booking', 'reserve', 'reservation', 'available', 'availability'],
                'response': """Thank you for your booking inquiry! Here's what you need to know:

📅 **How to Book:**
1. Browse our tours on the Tours page
2. Click "Book Now" on your preferred tour
3. Fill out the booking form with your details
4. Complete payment to confirm your reservation

💰 **Payment:** We accept major credit cards and mobile money
📞 **Questions?** Call us at +256 705 908 699
✉️ **Email:** affordablescapes@gmail.com

We'll process your booking within 24 hours and send you a confirmation email!"""
            },
            'pricing': {
                'keywords': ['price', 'cost', 'fee', 'money', 'payment', 'cheap', 'expensive', 'discount'],
                'response': """Here's information about our pricing:

💰 **Tour Prices:** Range from $50-$500 depending on destination and duration
🎯 **What's Included:** Transportation, accommodation, meals, and guided tours
💳 **Payment Options:** Credit cards, mobile money, bank transfer
🎁 **Group Discounts:** 10% off for groups of 5+ people
📅 **Early Bird:** Book 30 days in advance for 15% discount

Visit our Tours page to see specific prices for each destination!"""
            },
            'cancellation': {
                'keywords': ['cancel', 'cancellation', 'refund', 'reschedule', 'change'],
                'response': """Our cancellation and refund policy:

✅ **Free Cancellation:** Up to 48 hours before tour date
💰 **Refund Policy:**
  - 48+ hours: 100% refund
  - 24-48 hours: 50% refund  
  - Less than 24 hours: No refund

🔄 **Rescheduling:** Free within 7 days of original date
📞 **To Cancel:** Contact us immediately at +256 705 908 699

We understand plans change - we're here to help!"""
            },
            'general': {
                'keywords': ['hello', 'hi', 'help', 'info', 'about', 'what', 'where', 'when'],
                'response': """Welcome to Affordable Escapes! 🌍

We're your trusted travel partner offering amazing tours across Uganda and East Africa.

🏞️ **Our Tours:** National parks, cultural sites, adventure activities
🚌 **Services:** Transportation, accommodation, meals, expert guides
⭐ **Experience:** Over 5 years of creating memorable journeys

**Quick Actions:**
- Browse Tours: Check out our amazing destinations
- Book Now: Reserve your spot on any tour
- Contact Us: +256 705 908 699 or affordablescapes@gmail.com

What would you like to know more about?"""
            }
        }
    
    def analyze_inquiry(self, message, subject=""):
        """Analyze inquiry and determine if bot can handle it."""
        text = f"{subject} {message}".lower()
        
        # Find best matching category
        best_match = None
        max_matches = 0
        
        for category, data in self.responses.items():
            matches = 0
            for keyword in data['keywords']:
                if keyword in text:
                    matches += 1
            
            if matches > max_matches:
                max_matches = matches
                best_match = category
        
        # Calculate confidence based on keyword matches
        confidence = min(max_matches * 0.3, 1.0)
        
        # Check for complex patterns that need human attention
        human_keywords = ['complaint', 'problem', 'issue', 'angry', 'disappointed', 'terrible', 'awful']
        needs_human = any(word in text for word in human_keywords)
        
        return {
            'category': best_match,
            'confidence': confidence,
            'can_handle': confidence >= 0.6 and not needs_human,
            'needs_human': needs_human
        }
    
    def generate_response(self, category):
        """Generate response for a given category."""
        if category in self.responses:
            return self.responses[category]['response']
        return None
    
    def process_inquiry(self, inquiry):
        """Main method to process an inquiry."""
        analysis = self.analyze_inquiry(inquiry.message, inquiry.subject)
        
        result = {
            'analysis': analysis,
            'response': None,
            'can_handle': analysis['can_handle']
        }
        
        if analysis['can_handle'] and analysis['category']:
            result['response'] = self.generate_response(analysis['category'])
        
        return result


# Global bot instance
inquiry_bot = SimpleInquiryBot()
