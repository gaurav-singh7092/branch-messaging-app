'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { MessageSquare, Users, Search, Settings, LogOut, Bell, Wifi, WifiOff, UserPlus } from 'lucide-react';
import { API_ENDPOINTS, apiRequest } from '@/lib/api';
import { Agent, ConversationListItem, Customer } from '@/lib/types';
import { cn } from '@/lib/utils';
import { WebSocketProvider, useWebSocket } from '@/lib/websocket';
import ConversationList from './ConversationList';
import MessagePanel from './MessagePanel';
import CustomerPanel from './CustomerPanel';
import SearchModal from './SearchModal';
import CustomerSimulator from './CustomerSimulator';
import AddAgentModal from './AddAgentModal';

function DashboardContent() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [selectedConversation, setSelectedConversation] = useState<ConversationListItem | null>(null);
  const [showSearch, setShowSearch] = useState(false);
  const [showSimulator, setShowSimulator] = useState(false);
  const [showAddAgent, setShowAddAgent] = useState(false);
  const [activeTab, setActiveTab] = useState<'messages' | 'simulator'>('messages');
  const [conversationListKey, setConversationListKey] = useState(0);
  const { isConnected } = useWebSocket();

  // Callback to trigger conversation list refresh
  const handleConversationUpdate = useCallback(() => {
    // Increment key to force ConversationList to re-fetch
    setConversationListKey(prev => prev + 1);
  }, []);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const data = await apiRequest<Agent[]>(API_ENDPOINTS.agents);
        setAgents(data);
        if (data.length > 0 && !selectedAgent) {
          setSelectedAgent(data[0]);
        }
      } catch (error) {
        console.error('Error fetching agents:', error);
      }
    };

    fetchAgents();
  }, []);

  const handleAgentCreated = (newAgent: Agent) => {
    setAgents(prev => [...prev, newAgent]);
    setSelectedAgent(newAgent); // Auto-select the new agent
  };

  // Keyboard shortcut for search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowSearch(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSelectConversation = (conversation: ConversationListItem) => {
    setSelectedConversation(conversation);
    setActiveTab('messages');
  };

  const handleSelectCustomer = async (customer: Customer) => {
    // Find or create a conversation for this customer
    try {
      const conversations = await apiRequest<ConversationListItem[]>(
        `${API_ENDPOINTS.customers}/${customer.id}/conversations`
      );
      if (conversations.length > 0) {
        setSelectedConversation(conversations[0]);
        setActiveTab('messages');
      }
    } catch (error) {
      console.error('Error fetching customer conversations:', error);
    }
  };

  if (!selectedAgent) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-lg">
              <MessageSquare className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Branch Messaging</h1>
              <p className="text-xs text-gray-500">Agent Portal</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Connection Status */}
          <div className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-full text-sm",
            isConnected ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
          )}>
            {isConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>

          {/* Search Button */}
          <button
            onClick={() => setShowSearch(true)}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <Search className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-600">Search</span>
            <kbd className="px-2 py-0.5 text-xs bg-white rounded border border-gray-300 text-gray-500">
              ⌘K
            </kbd>
          </button>

          {/* Simulator Toggle */}
          <button
            onClick={() => setShowSimulator(!showSimulator)}
            className={cn(
              "px-4 py-2 rounded-lg transition-colors font-medium text-sm",
              showSimulator
                ? "bg-green-500 text-white"
                : "bg-gray-100 hover:bg-gray-200 text-gray-700"
            )}
          >
            {showSimulator ? 'Hide Simulator' : 'Customer Simulator'}
          </button>

          {/* Agent Selector */}
          <div className="flex items-center gap-2">
            <select
              value={selectedAgent?.id || ''}
              onChange={(e) => {
                const agent = agents.find(a => a.id === Number(e.target.value));
                if (agent) setSelectedAgent(agent);
              }}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            >
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => setShowAddAgent(true)}
              className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              title="Add New Agent"
            >
              <UserPlus className="w-4 h-4" />
            </button>
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Customer Simulator Panel */}
        {showSimulator && (
          <div className="w-80 flex-shrink-0 border-r border-gray-200 bg-gray-50 p-3 overflow-y-auto">
            <CustomerSimulator />
          </div>
        )}

        {/* Conversation List */}
        <div className="w-96">
          <ConversationList
            key={conversationListKey}
            selectedId={selectedConversation?.id || null}
            onSelect={handleSelectConversation}
            agentId={selectedAgent.id}
            onRefreshNeeded={handleConversationUpdate}
          />
        </div>

        {/* Message Panel */}
        <div className="flex-1 flex">
          {selectedConversation ? (
            <>
              <MessagePanel
                conversationId={selectedConversation.id}
                agentId={selectedAgent.id}
                onConversationUpdate={handleConversationUpdate}
              />
              {selectedConversation.customer_id && (
                <CustomerPanel customerId={selectedConversation.customer_id} />
              )}
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center bg-gray-50">
              <div className="text-center">
                <MessageSquare className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-gray-700 mb-2">
                  Select a conversation
                </h2>
                <p className="text-gray-500">
                  Choose a conversation from the list to start messaging
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Search Modal */}
      <SearchModal
        isOpen={showSearch}
        onClose={() => setShowSearch(false)}
        onSelectConversation={handleSelectConversation}
        onSelectCustomer={handleSelectCustomer}
      />

      {/* Add Agent Modal */}
      <AddAgentModal
        isOpen={showAddAgent}
        onClose={() => setShowAddAgent(false)}
        onAgentCreated={handleAgentCreated}
      />
    </div>
  );
}

export default function AgentDashboard() {
  const [agentId, setAgentId] = useState<number | null>(null);

  useEffect(() => {
    // For simplicity, we'll use agent ID 1 as default
    // In a real app, this would come from authentication
    setAgentId(1);
  }, []);

  if (!agentId) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <WebSocketProvider agentId={agentId}>
      <DashboardContent />
    </WebSocketProvider>
  );
}
