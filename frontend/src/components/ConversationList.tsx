'use client';

import { useState, useEffect, useCallback } from 'react';
import { Search, Filter, RefreshCw, AlertCircle, Clock, CheckCircle, XCircle, User, Users } from 'lucide-react';
import { API_ENDPOINTS, apiRequest } from '@/lib/api';
import { ConversationListItem, Priority, ConversationStatus, ConversationStats } from '@/lib/types';
import { cn, formatDate, getPriorityBadgeColor, getStatusColor, truncate } from '@/lib/utils';
import { useNewMessages, useConversationUpdates, useNewConversations } from '@/lib/websocket';

type AssignmentFilter = 'all' | 'mine' | 'unassigned' | 'others';

interface ConversationListProps {
  selectedId: number | null;
  onSelect: (conversation: ConversationListItem) => void;
  agentId: number;
  onRefreshNeeded?: () => void;
}

export default function ConversationList({ selectedId, onSelect, agentId, onRefreshNeeded }: ConversationListProps) {
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [stats, setStats] = useState<ConversationStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState<Priority | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<ConversationStatus | 'all'>('all');
  const [assignmentFilter, setAssignmentFilter] = useState<AssignmentFilter>('all');
  const [showFilters, setShowFilters] = useState(false);

  const fetchConversations = useCallback(async () => {
    try {
      let url = API_ENDPOINTS.conversations;
      const params = new URLSearchParams();
      
      if (priorityFilter !== 'all') params.append('priority', priorityFilter);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
      
      const data = await apiRequest<ConversationListItem[]>(url);
      setConversations(data);
    } catch (error) {
      console.error('Error fetching conversations:', error);
    } finally {
      setLoading(false);
    }
  }, [priorityFilter, statusFilter]);

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiRequest<ConversationStats>(API_ENDPOINTS.conversationStats);
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  }, []);

  useEffect(() => {
    fetchConversations();
    fetchStats();
  }, [fetchConversations, fetchStats]);

  // Handle real-time new messages
  const handleNewMessage = useCallback((data: unknown) => {
    const messageData = data as { conversation_id: number; content: string; is_from_customer: boolean; created_at: string; priority: string };
    setConversations(prev => {
      const index = prev.findIndex(c => c.id === messageData.conversation_id);
      if (index === -1) return prev;
      
      const updated = [...prev];
      const conversation = { ...updated[index] };
      conversation.updated_at = messageData.created_at;
      conversation.last_message = {
        id: Date.now(),
        conversation_id: messageData.conversation_id,
        content: messageData.content,
        is_from_customer: messageData.is_from_customer,
        priority: messageData.priority as Priority,
        created_at: messageData.created_at,
      };
      if (messageData.is_from_customer) {
        conversation.unread_count += 1;
      }
      updated[index] = conversation;
      
      // Re-sort by priority and updated time
      return updated.sort((a, b) => {
        const priorityOrder = { urgent: 4, high: 3, medium: 2, low: 1 };
        const aPriority = priorityOrder[a.priority] || 0;
        const bPriority = priorityOrder[b.priority] || 0;
        if (aPriority !== bPriority) return bPriority - aPriority;
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      });
    });
  }, []);

  // Handle conversation updates
  const handleConversationUpdate = useCallback((data: unknown) => {
    const updateData = data as { 
      id: number; 
      status?: string; 
      priority?: string; 
      agent_id?: number | null;
      agent_name?: string | null;
    };
    setConversations(prev => prev.map(conv => {
      if (conv.id === updateData.id) {
        // Handle agent_id - it can be a number, null, or undefined
        let newAgentId = conv.agent_id;
        let newAssignedAgent = conv.assigned_agent;
        
        if (updateData.agent_id !== undefined) {
          // agent_id was explicitly set (could be null for unassign or a number for assign)
          newAgentId = updateData.agent_id === null ? undefined : updateData.agent_id;
          newAssignedAgent = updateData.agent_id === null ? undefined : {
            id: updateData.agent_id,
            name: updateData.agent_name || `Agent ${updateData.agent_id}`,
            email: '',
            is_online: true,
            created_at: new Date().toISOString()
          };
        }
        
        return {
          ...conv,
          status: (updateData.status as ConversationStatus) || conv.status,
          priority: (updateData.priority as Priority) || conv.priority,
          agent_id: newAgentId,
          assigned_agent: newAssignedAgent,
        };
      }
      return conv;
    }));
    fetchStats();
  }, [fetchStats]);

  // Handle new conversations
  const handleNewConversation = useCallback((data: unknown) => {
    const newConv = data as { id: number; customer_id: number; priority: string; status: string; subject: string; customer_name: string; customer_email: string };
    const newConversation: ConversationListItem = {
      id: newConv.id,
      customer_id: newConv.customer_id,
      status: newConv.status as ConversationStatus,
      priority: newConv.priority as Priority,
      subject: newConv.subject,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      customer: {
        id: newConv.customer_id,
        name: newConv.customer_name,
        email: newConv.customer_email,
        account_status: 'active',
        account_created: new Date().toISOString(),
        last_activity: new Date().toISOString(),
      },
      unread_count: 1,
    };
    
    setConversations(prev => [newConversation, ...prev]);
    fetchStats();
  }, [fetchStats]);

  useNewMessages(handleNewMessage);
  useConversationUpdates(handleConversationUpdate);
  useNewConversations(handleNewConversation);

  // Filter by search query and assignment
  const filteredConversations = conversations.filter(conv => {
    // Assignment filter
    if (assignmentFilter === 'mine' && conv.agent_id !== agentId) return false;
    if (assignmentFilter === 'unassigned' && conv.agent_id !== null && conv.agent_id !== undefined) return false;
    if (assignmentFilter === 'others' && (conv.agent_id === null || conv.agent_id === undefined || conv.agent_id === agentId)) return false;
    
    // Search filter
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      conv.customer?.name?.toLowerCase().includes(query) ||
      conv.customer?.email?.toLowerCase().includes(query) ||
      conv.subject?.toLowerCase().includes(query) ||
      conv.last_message?.content?.toLowerCase().includes(query)
    );
  });

  // Get assignment badge for a conversation
  const getAssignmentBadge = (conv: ConversationListItem) => {
    if (conv.agent_id === null || conv.agent_id === undefined) {
      return (
        <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-700 rounded-full border border-yellow-200">
          <Users className="w-3 h-3" />
          Unassigned
        </span>
      );
    }
    if (conv.agent_id === agentId) {
      return (
        <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded-full border border-green-200">
          <User className="w-3 h-3" />
          You
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-700 rounded-full border border-purple-200">
        <User className="w-3 h-3" />
        {conv.assigned_agent?.name || 'Other Agent'}
      </span>
    );
  };

  const getPriorityIcon = (priority: Priority) => {
    switch (priority) {
      case 'urgent':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'high':
        return <AlertCircle className="w-4 h-4 text-orange-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="h-full flex flex-col bg-white border-r border-gray-200">
      {/* Stats Bar */}
      {stats && (
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4 text-blue-500" />
                <span className="text-gray-600">Open:</span>
                <span className="font-medium">{stats.by_status.open || 0}</span>
              </span>
              <span className="flex items-center gap-1">
                <AlertCircle className="w-4 h-4 text-red-500" />
                <span className="text-gray-600">Urgent:</span>
                <span className="font-medium text-red-600">{stats.by_priority.urgent || 0}</span>
              </span>
            </div>
            <span className="text-gray-500">
              Unassigned: {stats.unassigned}
            </span>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="p-4 border-b border-gray-200 space-y-3">
        {/* Assignment Filter Tabs */}
        <div className="flex bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setAssignmentFilter('all')}
            className={cn(
              "flex-1 px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
              assignmentFilter === 'all' 
                ? "bg-white text-gray-900 shadow-sm" 
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            All
          </button>
          <button
            onClick={() => setAssignmentFilter('mine')}
            className={cn(
              "flex-1 px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
              assignmentFilter === 'mine' 
                ? "bg-green-500 text-white shadow-sm" 
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            Mine
          </button>
          <button
            onClick={() => setAssignmentFilter('unassigned')}
            className={cn(
              "flex-1 px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
              assignmentFilter === 'unassigned' 
                ? "bg-yellow-500 text-white shadow-sm" 
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            Unassigned
          </button>
          <button
            onClick={() => setAssignmentFilter('others')}
            className={cn(
              "flex-1 px-3 py-1.5 text-sm font-medium rounded-md transition-colors",
              assignmentFilter === 'others' 
                ? "bg-purple-500 text-white shadow-sm" 
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            Others
          </button>
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          />
        </div>
        
        <div className="flex items-center justify-between">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              "flex items-center gap-1 text-sm px-2 py-1 rounded",
              showFilters ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:bg-gray-100"
            )}
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <button
            onClick={() => {
              setLoading(true);
              fetchConversations();
              fetchStats();
            }}
            className="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
          >
            <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          </button>
        </div>

        {showFilters && (
          <div className="flex gap-2">
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value as Priority | 'all')}
              className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Priorities</option>
              <option value="urgent">Urgent</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as ConversationStatus | 'all')}
              className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Statuses</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        )}
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
          </div>
        ) : filteredConversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500">
            <p>No conversations found</p>
          </div>
        ) : (
          filteredConversations.map((conversation) => (
            <div
              key={conversation.id}
              onClick={() => onSelect(conversation)}
              className={cn(
                "p-4 border-b border-gray-100 cursor-pointer transition-colors",
                selectedId === conversation.id
                  ? "bg-blue-50 border-l-4 border-l-blue-500"
                  : "hover:bg-gray-50",
                conversation.priority === 'urgent' && selectedId !== conversation.id && "bg-red-50",
                // Add left border color based on assignment
                conversation.agent_id === agentId && selectedId !== conversation.id && "border-l-4 border-l-green-400",
                conversation.agent_id !== null && conversation.agent_id !== undefined && conversation.agent_id !== agentId && selectedId !== conversation.id && "border-l-4 border-l-purple-400 opacity-75"
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    {getPriorityIcon(conversation.priority)}
                    <span className="font-medium text-gray-900 truncate">
                      {conversation.customer?.name || 'Unknown Customer'}
                    </span>
                    {conversation.unread_count > 0 && (
                      <span className="px-1.5 py-0.5 text-xs font-medium bg-blue-500 text-white rounded-full">
                        {conversation.unread_count}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 truncate mt-0.5">
                    {conversation.customer?.email}
                  </p>
                </div>
                <span className="text-xs text-gray-400 whitespace-nowrap">
                  {formatDate(conversation.updated_at)}
                </span>
              </div>
              
              <p className="mt-2 text-sm text-gray-600 line-clamp-2">
                {conversation.last_message?.content || conversation.subject || 'No messages'}
              </p>
              
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {/* Agent Assignment Badge - Shown First */}
                {getAssignmentBadge(conversation)}
                <span className={cn(
                  "px-2 py-0.5 text-xs font-medium rounded-full border",
                  getPriorityBadgeColor(conversation.priority)
                )}>
                  {conversation.priority}
                </span>
                <span className={cn(
                  "px-2 py-0.5 text-xs font-medium rounded-full",
                  getStatusColor(conversation.status)
                )}>
                  {conversation.status.replace('_', ' ')}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
