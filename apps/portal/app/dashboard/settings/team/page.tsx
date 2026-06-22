"use client";
import { useState } from "react";

const ROLE_COLORS: Record<string, string> = {
  owner: "bg-purple-100 text-purple-800 border-purple-200",
  admin: "bg-red-50 text-red-700 border-red-200",
  operator: "bg-green-50 text-green-700 border-green-200",
  auditor: "bg-blue-50 text-blue-700 border-blue-200",
  viewer: "bg-slate-100 text-slate-500 border-slate-200",
};

const MOCK_MEMBERS = [
  { id: "1", name: "Omar Rao", email: "omar.rao@acmecorp.com", role: "owner", joined: "2026-01-01", last_active: "Today" },
  { id: "2", name: "Sarah Chen", email: "s.chen@acmecorp.com", role: "admin", joined: "2026-02-03", last_active: "Yesterday" },
  { id: "3", name: "Rachel Moore", email: "r.moore@acmecorp.com", role: "auditor", joined: "2026-04-01", last_active: "Jun 21" },
  { id: "4", name: "Maria Santos", email: "m.santos@acmecorp.com", role: "operator", joined: "2026-03-05", last_active: "Today" },
  { id: "5", name: "Lisa Wang", email: "l.wang@acmecorp.com", role: "viewer", joined: "2026-05-02", last_active: "Jun 17" },
];

const MOCK_INVITES = [
  { id: "i1", email: "john.doe@acmecorp.com", role: "auditor", invited_by: "Omar Rao", expires: "Jun 29" },
  { id: "i2", email: "finance@acmecorp.com", role: "viewer", invited_by: "Sarah Chen", expires: "Jun 28" },
];

export default function TeamPage() {
  const [members, setMembers] = useState(MOCK_MEMBERS);
  const [invites, setInvites] = useState(MOCK_INVITES);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteForm, setInviteForm] = useState({ email: "", role: "auditor" });

  return (
    <div className="p-7 bg-slate-50 min-h-screen">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Team Management</h1>
            <p className="text-sm text-slate-400 mt-1">Manage members, roles, and pending invitations</p>
          </div>
          <button onClick={() => setShowInvite(true)} className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-semibold rounded-md">
            + Invite Member
          </button>
        </div>

        {showInvite && (
          <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900 mb-4">Invite Member</h2>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Email Address</label>
                <input value={inviteForm.email} onChange={e => setInviteForm({...inviteForm, email: e.target.value})} placeholder="colleague@company.com" className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm outline-none focus:border-green-400" />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Role</label>
                <select value={inviteForm.role} onChange={e => setInviteForm({...inviteForm, role: e.target.value})} className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm outline-none focus:border-green-400 bg-white">
                  <option value="admin">Admin</option>
                  <option value="operator">Operator</option>
                  <option value="auditor">Auditor</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowInvite(false)} className="px-4 py-2 text-sm text-slate-500 border border-slate-200 rounded-md hover:bg-slate-50">Cancel</button>
              <button className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-semibold rounded-md">Send Invite</button>
            </div>
          </div>
        )}

        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden mb-5">
          <div className="px-5 py-3.5 border-b border-slate-100">
            <span className="text-sm font-bold text-slate-900">Members ({members.length})</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                {["Name", "Email", "Role", "Joined", "Last Active", "Actions"].map(h => (
                  <th key={h} className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-5 py-2.5 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {members.map(m => (
                <tr key={m.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-5 py-3 text-sm font-semibold text-slate-900">{m.name}</td>
                  <td className="px-5 py-3 text-sm text-slate-500">{m.email}</td>
                  <td className="px-5 py-3">
                    <span className={`text-xs font-bold border px-2 py-0.5 rounded capitalize ${ROLE_COLORS[m.role]}`}>{m.role}</span>
                  </td>
                  <td className="px-5 py-3 text-xs text-slate-400">{new Date(m.joined).toLocaleDateString()}</td>
                  <td className="px-5 py-3 text-xs text-slate-400">{m.last_active}</td>
                  <td className="px-5 py-3 flex gap-2">
                    {m.role !== "owner" && <>
                      <button className="text-xs text-slate-400 hover:text-green-600 font-semibold">Change Role</button>
                      <button className="text-xs text-slate-400 hover:text-red-500 font-semibold">Remove</button>
                    </>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100">
            <span className="text-sm font-bold text-slate-900">Pending Invites ({invites.length})</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                {["Email", "Role", "Invited By", "Expires", "Actions"].map(h => (
                  <th key={h} className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-5 py-2.5 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {invites.map(inv => (
                <tr key={inv.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-5 py-3 text-sm text-slate-700">{inv.email}</td>
                  <td className="px-5 py-3"><span className={`text-xs font-bold border px-2 py-0.5 rounded capitalize ${ROLE_COLORS[inv.role]}`}>{inv.role}</span></td>
                  <td className="px-5 py-3 text-sm text-slate-500">{inv.invited_by}</td>
                  <td className="px-5 py-3 text-xs text-amber-600 font-semibold">{inv.expires}</td>
                  <td className="px-5 py-3 flex gap-2">
                    <button className="text-xs text-slate-400 hover:text-green-600 font-semibold">Resend</button>
                    <button className="text-xs text-slate-400 hover:text-red-500 font-semibold">Revoke</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
