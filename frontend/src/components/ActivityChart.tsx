import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

type ActivityDay = { day: string; failed: number; passed: number }

export default function ActivityChart({ data }: { data: ActivityDay[] }) {
  return (
    <div className="activity-chart">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
          <defs>
            <linearGradient id="failedFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ed8e67" stopOpacity={0.24} />
              <stop offset="95%" stopColor="#ed8e67" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 5" stroke="#263230" vertical={false} />
          <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#899791', fontSize: 11 }} dy={8} />
          <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fill: '#899791', fontSize: 10 }} />
          <Tooltip contentStyle={{ background: '#17201f', border: '1px solid #34413e', borderRadius: 7, color: '#e6ece9', fontSize: 12 }} />
          <Area type="monotone" dataKey="failed" name="Failed" stroke="#e88b66" strokeWidth={2} fill="url(#failedFill)" />
          <Area type="monotone" dataKey="passed" name="Passed" stroke="#61c9a4" strokeWidth={2} fill="transparent" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
