import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { NotificationsPage } from './NotificationsPage';
import { NotificationBell } from '../components/NotificationBell';
const mocks=vi.hoisted(()=>({api:vi.fn()}));
const notice={id:'1',entity_type:'order',entity_id:'9007199254740993',title:'Order placed',body:'Update',created_at:'2026-11-25T00:00:00Z',read_at:null};

vi.mock('../state/AuthContext',()=>({useAuth:()=>({user:{role:'BUYER',name:'Buyer'}})}));
vi.mock('../components/Shared',()=>({DashboardShell:({children}:{children:React.ReactNode})=><div>{children}</div>,PageTop:({title}:{title:string})=><h1>{title}</h1>,EmptyState:()=>null}));
vi.mock('../api/client',()=>({identifier:(id:string)=>{if(!/^\d+$/.test(id))throw Error('Invalid ID');return id;},errorMessage:()=>'',api:mocks.api}));
beforeEach(()=>{mocks.api.mockReset();mocks.api.mockImplementation(async(path:string)=>path.includes('unread-count')?{count:2}:[{...notice,entity_type:'professional'},{...notice,id:'2',entity_type:'creative'}]);});
it('routes professional and creative notifications to their own workspaces',async()=>{
  render(<MemoryRouter><NotificationsPage/></MemoryRouter>);
  const links=await screen.findAllByRole('link',{name:'View update'});
  expect(links[0]).toHaveAttribute('href','/buyer/professional');
  expect(links[1]).toHaveAttribute('href','/buyer/creative');
});
it('shows read status, semantic timestamp and exact owned order link; refreshes bell after mark all',async()=>{
  mocks.api.mockImplementation(async(path:string)=>path.includes('unread-count')?{count:2}:[notice]);
  render(<MemoryRouter><NotificationBell/><NotificationsPage/></MemoryRouter>);
  expect(await screen.findByRole('link',{name:'Notifications, 2 unread'})).toBeInTheDocument();
  expect(await screen.findByText('Unread')).toBeInTheDocument();expect(screen.getByRole('link',{name:'View update'})).toHaveAttribute('href','/buyer/orders/9007199254740993');expect(document.querySelector('time')).toHaveAttribute('datetime',notice.created_at);
  mocks.api.mockImplementation(async(path:string)=>path.includes('unread-count')?{count:0}:path.includes('/read')?{}:[{...notice,read_at:'2026-11-25T01:00:00Z'}]);
  fireEvent.click(screen.getByRole('button',{name:'Mark all as read'}));
  expect(await screen.findByRole('link',{name:'Notifications, 0 unread'})).toBeInTheDocument();expect(await screen.findByText('Read')).toBeInTheDocument();expect(mocks.api).toHaveBeenCalledWith('/notifications/read-all',{method:'PATCH'});
});
it('does not generate unrelated links for unknown entities or malformed order IDs',async()=>{
 mocks.api.mockImplementation(async(path:string)=>path.includes('unread-count')?{count:2}:[{...notice,entity_id:'../../seller/2'},{...notice,id:'2',entity_type:'unknown'}]);
 render(<MemoryRouter><NotificationsPage/></MemoryRouter>);await screen.findAllByText('Order placed');expect(screen.queryByRole('link',{name:'View update'})).not.toBeInTheDocument();
});
it('discards a late page response after returning to the earlier page',async()=>{
 let finish!:(value:unknown)=>void;let loads=0;
 mocks.api.mockImplementation((path:string)=>{if(path.includes('unread-count'))return Promise.resolve({count:1});if(path.includes('offset=50'))return new Promise(resolve=>{finish=resolve;});loads++;return Promise.resolve(Array.from({length:50},(_,id)=>({...notice,id:String(id+1),title:'First page'})));});
 render(<MemoryRouter><NotificationsPage/></MemoryRouter>);await screen.findAllByText('First page');fireEvent.click(screen.getByRole('button',{name:'More updates'}));await waitFor(()=>expect(finish).toBeDefined());fireEvent.click(screen.getByRole('button',{name:'Previous updates'}));await waitFor(()=>expect(loads).toBe(2));finish([{...notice,title:'Stale page'}]);expect(await screen.findAllByText('First page')).toHaveLength(50);expect(screen.queryByText('Stale page')).not.toBeInTheDocument();
});
