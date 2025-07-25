class TravelChatbot {
    constructor() {
        this.isOpen = false;
        this.messages = [];
        this.init();
    }

    init() {
        this.createChatbotHTML();
        this.bindEvents();
        this.addInitialMessage();
    }

    createChatbotHTML() {
        const chatbotHTML = `
            <!-- Chatbot Toggle Button -->
            <div id="chatbot-toggle" class="chatbot-toggle">
                <i class="fas fa-comments"></i>
            </div>

            <!-- Chatbot Container -->
            <div id="chatbot-container" class="chatbot-container">
                <div class="chatbot-header">
                    <div class="chatbot-title">
                        <i class="fas fa-robot me-2"></i>
                        Travel Assistant
                    </div>
                    <button id="chatbot-close" class="chatbot-close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div id="chatbot-messages" class="chatbot-messages">
                    <!-- Messages will be added here -->
                </div>
                <div class="chatbot-input-container">
                    <input type="text" id="chatbot-input" placeholder="Type your question..." maxlength="200">
                    <button id="chatbot-send">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', chatbotHTML);
    }

    bindEvents() {
        const toggle = document.getElementById('chatbot-toggle');
        const close = document.getElementById('chatbot-close');
        const send = document.getElementById('chatbot-send');
        const input = document.getElementById('chatbot-input');

        toggle.addEventListener('click', () => this.toggleChatbot());
        close.addEventListener('click', () => this.closeChatbot());
        send.addEventListener('click', () => this.sendMessage());
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
    }

    addInitialMessage() {
        this.addMessage('How can I help you?', 'bot');
        this.addQuickActions();
    }

    addQuickActions() {
        const quickActions = [
            'How do I book a tour?',
            'What services do you offer?',
            'How can I contact you?',
            'Where can I see available tours?'
        ];

        const actionsHTML = quickActions.map(action => 
            `<button class="quick-action-btn" onclick="chatbot.handleQuickAction('${action}')">${action}</button>`
        ).join('');

        const messagesContainer = document.getElementById('chatbot-messages');
        messagesContainer.insertAdjacentHTML('beforeend', `
            <div class="quick-actions">
                <div class="quick-actions-title">Quick questions:</div>
                ${actionsHTML}
            </div>
        `);
    }

    toggleChatbot() {
        this.isOpen = !this.isOpen;
        const container = document.getElementById('chatbot-container');
        const toggle = document.getElementById('chatbot-toggle');
        
        if (this.isOpen) {
            container.classList.add('open');
            toggle.classList.add('active');
        } else {
            container.classList.remove('open');
            toggle.classList.remove('active');
        }
    }

    closeChatbot() {
        this.isOpen = false;
        const container = document.getElementById('chatbot-container');
        const toggle = document.getElementById('chatbot-toggle');
        container.classList.remove('open');
        toggle.classList.remove('active');
    }

    sendMessage() {
        const input = document.getElementById('chatbot-input');
        const message = input.value.trim();
        
        if (message) {
            this.addMessage(message, 'user');
            input.value = '';
            
            // Simulate thinking delay
            setTimeout(() => {
                this.generateResponse(message);
            }, 500);
        }
    }

    handleQuickAction(action) {
        this.addMessage(action, 'user');
        setTimeout(() => {
            this.generateResponse(action);
        }, 500);
    }

    addMessage(text, sender) {
        const messagesContainer = document.getElementById('chatbot-messages');
        const messageHTML = `
            <div class="message ${sender}">
                <div class="message-content">
                    ${text}
                </div>
                <div class="message-time">
                    ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                </div>
            </div>
        `;
        
        messagesContainer.insertAdjacentHTML('beforeend', messageHTML);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    generateResponse(userMessage) {
        const message = userMessage.toLowerCase();
        let response = '';

        if (message.includes('book') || message.includes('booking')) {
            response = `To book a tour, you can:
            <br>• Visit our <a href="/tours" style="color: #0066ff;">Tours page</a> to browse available options
            <br>• Click on any tour to see details and book
            <br>• Or go to your <a href="/dashboard" style="color: #0066ff;">Dashboard</a> to manage bookings`;
        }
        else if (message.includes('service') || message.includes('what do you offer')) {
            response = `We offer various travel services! Check out our <a href="/services" style="color: #0066ff;">Services page</a> to see:
            <br>• Tour packages
            <br>• Travel planning
            <br>• Custom itineraries
            <br>• And much more!`;
        }
        else if (message.includes('contact') || message.includes('reach')) {
            response = `You can contact us through our <a href="/contact" style="color: #0066ff;">Contact page</a> where you'll find:
            <br>• Contact form
            <br>• Phone numbers
            <br>• Email addresses
            <br>• Office locations`;
        }
        else if (message.includes('tour') || message.includes('available')) {
            response = `Browse all our available tours on the <a href="/tours" style="color: #0066ff;">Tours page</a>. You can filter by:
            <br>• Destination
            <br>• Price range
            <br>• Duration
            <br>• Tour type`;
        }
        else if (message.includes('about') || message.includes('company')) {
            response = `Learn more about Affordable Escapes on our <a href="/about" style="color: #0066ff;">About page</a> where you can read about our mission and team.`;
        }
        else if (message.includes('dashboard') || message.includes('account')) {
            response = `Your <a href="/dashboard" style="color: #0066ff;">Dashboard</a> is where you can:
            <br>• View your bookings
            <br>• Manage your profile
            <br>• Track your travel history`;
        }
        else if (message.includes('home') || message.includes('main')) {
            response = `You can return to our <a href="/" style="color: #0066ff;">Home page</a> anytime by clicking the "Affordable Escapes" logo in the navigation bar.`;
        }
        else if (message.includes('help') || message.includes('navigation') || message.includes('navigate')) {
            response = `Here's how to navigate our website:
            <br>• <strong>Home:</strong> Main page with featured content
            <br>• <strong>Tours:</strong> Browse and book travel packages
            <br>• <strong>Services:</strong> Learn about what we offer
            <br>• <strong>About:</strong> Company information
            <br>• <strong>Contact:</strong> Get in touch with us
            <br>• <strong>Dashboard:</strong> Your personal account area`;
        }
        else {
            response = `I'd be happy to help! Here are some things I can assist you with:
            <br>• Finding tours and booking information
            <br>• Explaining our services
            <br>• Providing contact details
            <br>• Helping you navigate the website
            <br><br>Try asking me about booking tours, our services, or how to contact us!`;
        }

        this.addMessage(response, 'bot');
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.chatbot = new TravelChatbot();
});
