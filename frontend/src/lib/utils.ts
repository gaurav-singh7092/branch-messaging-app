import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  const d = new Date(date);
  const now = new Date();
  
  // Ensure we're comparing UTC times properly
  // If the date string doesn't have timezone info, treat it as UTC
  const dateStr = typeof date === 'string' ? date : date.toISOString();
  const isUTC = !dateStr.includes('+') && !dateStr.includes('Z') && !dateStr.match(/[+-]\d{2}:\d{2}$/);
  
  // If the timestamp appears to be UTC without a Z suffix, add it
  const normalizedDate = isUTC && typeof date === 'string' && !date.endsWith('Z') 
    ? new Date(date + 'Z') 
    : d;
  
  const diff = now.getTime() - normalizedDate.getTime();
  
  // Less than a minute
  if (diff < 60000) {
    return 'Just now';
  }
  
  // Less than an hour
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000);
    return `${minutes}m ago`;
  }
  
  // Less than a day
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    return `${hours}h ago`;
  }
  
  // Less than a week
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000);
    return `${days}d ago`;
  }
  
  // Format as date
  return normalizedDate.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: normalizedDate.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  });
}

export function formatTime(date: string | Date): string {
  // Handle UTC timestamps from backend (without Z suffix)
  const dateStr = typeof date === 'string' ? date : date.toISOString();
  const isUTC = !dateStr.includes('+') && !dateStr.includes('Z') && !dateStr.match(/[+-]\d{2}:\d{2}$/);
  
  const normalizedDate = isUTC && typeof date === 'string' && !date.endsWith('Z')
    ? new Date(date + 'Z')
    : new Date(date);
    
  return normalizedDate.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function getPriorityColor(priority: string): string {
  switch (priority) {
    case 'urgent':
      return 'bg-red-500 text-white';
    case 'high':
      return 'bg-orange-500 text-white';
    case 'medium':
      return 'bg-yellow-500 text-white';
    case 'low':
      return 'bg-green-500 text-white';
    default:
      return 'bg-gray-500 text-white';
  }
}

export function getPriorityBadgeColor(priority: string): string {
  switch (priority) {
    case 'urgent':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'high':
      return 'bg-orange-100 text-orange-800 border-orange-200';
    case 'medium':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'low':
      return 'bg-green-100 text-green-800 border-green-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'open':
      return 'bg-blue-100 text-blue-800';
    case 'in_progress':
      return 'bg-purple-100 text-purple-800';
    case 'resolved':
      return 'bg-green-100 text-green-800';
    case 'closed':
      return 'bg-gray-100 text-gray-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}
