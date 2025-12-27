# Branch Messaging Application

A full-featured customer messaging platform for Branch that enables agents to efficiently respond to customer inquiries with real-time messaging, priority detection, multi-agent collaboration, and smart features.

## 🌟 Features

### Core Features
- **Real-time Messaging**: WebSocket-powered instant message delivery
- **Multi-Agent Collaboration**: Multiple agents can work independently with exclusive conversation assignment
- **Priority Detection**: Message urgency classification (Urgent, High, Medium, Low)
- **Search Functionality**: Search across messages and customers with filters
- **Customer Context Panel**: View customer profiles, loan status, and conversation history
- **Canned Messages**: Pre-configured quick responses with shortcuts
- **Adaptive Message Input**: Auto-resizing textarea for long messages
- **Add Agent UI**: Create new agents directly from the dashboard

### Multi-Agent System
- **Exclusive Assignment**: No two agents can be assigned to the same customer conversation
- **Assignment Filters**: Filter conversations by "All", "Mine", "Unassigned", or "Others"
- **Visual Indicators**: Color-coded badges show assignment status:
  - 🟢 **Green**: Assigned to you
  - 🟡 **Yellow**: Unassigned (available to claim)
  - 🟣 **Purple**: Assigned to another agent
- **Claim/Release**: Agents can claim unassigned conversations or release their own
- **Access Control**: Agents cannot send messages to conversations assigned to others

### Priority Detection
Messages are automatically classified based on keywords:
- **Urgent**: Loan disbursement issues, medical emergencies, fraud/security concerns
- **High**: Loan applications, payment failures, account access issues
- **Medium**: General inquiries, feature questions, account updates
- **Low**: Feedback, greetings, general appreciation

### Real-time Updates
- New messages appear instantly without page refresh
- Conversation list auto-updates with new conversations
- Priority and status changes sync across all connected agents
- Agent assignment changes broadcast to all connected users
- **Assignment badge sync**: Sidebar badges update immediately when conversations are assigned/released
- Connection status indicator

## 🏗️ Architecture

```
branch-messaging-app/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   │   ├── agents.py
│   │   │   ├── canned_messages.py
│   │   │   ├── conversations.py
│   │   │   ├── customers.py
│   │   │   ├── external.py
│   │   │   ├── search.py
│   │   │   └── websocket.py
│   │   ├── models/         # SQLAlchemy models
│   │   ├── services/       # Business logic
│   │   │   ├── priority_service.py
│   │   │   └── websocket_manager.py
│   │   ├── database.py     # Database configuration
│   │   ├── schemas.py      # Pydantic schemas
│   │   └── main.py         # FastAPI application
│   ├── data/
│   │   └── seed.py         # Database seeder
│   └── requirements.txt
├── frontend/               # Next.js Frontend
│   ├── src/
│   │   ├── app/           # Next.js app router
│   │   ├── components/    # React components
│   │   │   ├── AddAgentModal.tsx
│   │   │   ├── AgentDashboard.tsx
│   │   │   ├── CannedMessagePicker.tsx
│   │   │   ├── ConversationList.tsx
│   │   │   ├── CustomerPanel.tsx
│   │   │   ├── CustomerSimulator.tsx
│   │   │   ├── MessagePanel.tsx
│   │   │   └── SearchModal.tsx
│   │   └── lib/           # Utilities, API, types
│   └── package.json
├── GeneralistRails_Project_MessageData.csv  # Customer message data
├── postman_collection.json # API testing collection
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm or yarn

### Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd branch-messaging-app/backend
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Seed the database with sample data**:
   ```bash
   python data/seed.py
   ```

5. **Start the backend server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative Docs: `http://localhost:8000/redoc`

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd branch-messaging-app/frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```

The application will be available at `http://localhost:3000`

## 📡 API Endpoints

### External Messages (Customer-facing)
- `POST /api/external/messages` - Send a message as a customer

### Conversations
- `GET /api/conversations` - List all conversations (with filters)
- `GET /api/conversations/stats` - Get conversation statistics
- `GET /api/conversations/{id}` - Get conversation details
- `PUT /api/conversations/{id}` - Update conversation (status/priority/agent)
- `POST /api/conversations/{id}/messages` - Send agent message
- `POST /api/conversations/{id}/read` - Mark messages as read
- `POST /api/conversations/{id}/assign/{agent_id}` - Assign conversation to agent
- `POST /api/conversations/{id}/release?agent_id={id}` - Release conversation (unassign)

**Query Parameters for GET /api/conversations:**
- `status` - Filter by status (open, in_progress, resolved, closed)
- `priority` - Filter by priority (urgent, high, medium, low)
- `agent_id` - Filter by assigned agent
- `unassigned` - Filter for unassigned conversations only

### Customers
- `GET /api/customers` - List customers (with search)
- `GET /api/customers/{id}` - Get customer details
- `GET /api/customers/{id}/conversations` - Get customer's conversations
- `POST /api/customers/{id}/messages` - Send message as customer

### Agents
- `GET /api/agents` - List all agents
- `POST /api/agents` - Create new agent
- `PUT /api/agents/{id}/online` - Set agent online
- `PUT /api/agents/{id}/offline` - Set agent offline

### Canned Messages
- `GET /api/canned-messages` - List canned messages
- `GET /api/canned-messages/categories` - Get categories
- `POST /api/canned-messages` - Create canned message
- `PUT /api/canned-messages/{id}` - Update canned message
- `DELETE /api/canned-messages/{id}` - Delete canned message
- `POST /api/canned-messages/{id}/use` - Increment usage count

### Search
- `GET /api/search?q={query}` - Search conversations and customers

### WebSocket
- `WS /ws?agent_id={id}` - Real-time messaging connection

## 🧪 Testing with Postman

1. Import the `postman_collection.json` file into Postman
2. The collection includes all API endpoints organized by category
3. Use the "External Messages" folder to simulate customer messages
4. Watch the agent portal update in real-time!

## 🎨 Frontend Features

### Agent Dashboard
- **Agent Selector**: Switch between different agent accounts to test multi-agent functionality
- **Add Agent Button**: Create new agents directly from the UI (blue + button next to agent selector)
- **Conversation List**: Shows all conversations sorted by priority
- **Real-time Stats**: Open, urgent, and unassigned conversation counts
- **Assignment Tabs**: Filter by All, Mine, Unassigned, or Others
- **Priority/Status Filters**: Additional filtering options
- **Search**: Quick search across all conversations

### Conversation List
- **Visual Assignment Indicators**: 
  - Green left border for your conversations
  - Purple left border (dimmed) for other agents' conversations
  - Color-coded badges showing assignment status
- **Real-time Badge Sync**: Assignment badges update instantly when conversations are claimed or released
- **Priority Icons**: Visual indicators for urgent/high priority items
- **Unread Counter**: Badge showing unread message count
- **Real-time Updates**: List updates automatically via WebSocket

### Message Panel
- **Real-time Chat**: Messages appear instantly via WebSocket
- **Adaptive Text Input**: Auto-resizing textarea for long messages (supports Shift+Enter for new lines)
- **Assignment Status Banner**: Shows who owns the conversation
- **Claim/Release Buttons**: Manage conversation ownership
- **Access Control**: Blocked from sending messages to other agents' conversations
- **Priority/Status Controls**: Change conversation priority and status
- **Canned Messages**: Quick access to pre-written responses

### Customer Panel
- **Profile Information**: Name, email, account status
- **Loan Details**: Current loan status and amount
- **Activity History**: Previous conversations
- **Notes**: Customer-specific notes

### Customer Simulator
- Built-in tool to simulate customer messages
- Pre-written sample messages for testing
- Tests the full real-time pipeline

## 🔧 Configuration

### Environment Variables

**Backend** (optional):
```bash
DATABASE_URL=sqlite+aiosqlite:///./branch_messaging.db
```

**Frontend**:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## 📊 Database Schema

### Tables
- **customers**: Customer profiles and account information
- **agents**: Support agent profiles
- **conversations**: Customer-agent conversation threads
- **messages**: Individual messages within conversations
- **canned_messages**: Pre-configured response templates

## 🔒 Security Notes

This is a demonstration application. For production use, implement:
- Authentication (JWT, OAuth, etc.)
- Rate limiting
- Input sanitization
- HTTPS/WSS
- Database encryption
- Audit logging

## 📝 Sample Data

The seed script creates:
- 4 sample agents (Sarah Johnson, Mike Chen, Emily Davis, James Wilson)
- 55 customer conversations from the GeneralistRails CSV file
- 12 canned message templates across 4 categories
- Various priority levels and statuses

### Data Source
Customer messages are loaded from `GeneralistRails_Project_MessageData.csv` which contains real customer service interactions with:
- User IDs grouped into conversations
- Timestamps in UTC
- Message content

## 🚧 Future Enhancements

- [ ] Agent authentication with JWT
- [ ] File attachments
- [ ] Message templates with variables
- [ ] Analytics dashboard
- [ ] Mobile responsive design improvements

## 📄 License

MIT License - Feel free to use and modify for your needs.
