import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  Factory,
  Zap,
  CheckCircle,
  ArrowUp,
  ArrowDown,
  Loader2,
} from "lucide-react";
import { API_BASE_URL } from "../config";

const StatCard = ({ label, value, icon: Icon, color, delay }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.5 }}
      whileHover={{ y: -5 }}
      className="bg-white rounded-xl shadow-lg hover:shadow-2xl transition p-6 border-t-2 border-eco-green-500 group"
    >
      <div className="flex justify-between items-start mb-4">
        <div>
          <p className="text-gray-500 text-sm font-semibold tracking-wide uppercase">
            {label}
          </p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
        </div>
        <div
          className={`p-3 rounded-lg ${color} group-hover:scale-110 transition`}
        >
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          whileInView={{ width: "100%" }}
          viewport={{ once: true }}
          transition={{ delay: delay + 0.2, duration: 0.8 }}
          className="bg-gradient-to-r from-eco-green-500 to-blue-500 h-full rounded-full"
        />
      </div>
    </motion.div>
  );
};

const AnimatedBar = ({ pctHeight, actualValue, label, delay }) => {
  return (
    <motion.div className="flex-1 flex flex-col items-center">
      <motion.div
        initial={{ height: 0 }}
        whileInView={{ height: `${pctHeight}%` }}
        viewport={{ once: true }}
        transition={{ delay, duration: 0.8, ease: "easeOut" }}
        className="w-full bg-gradient-to-t from-eco-green-500 via-eco-green-400 to-blue-400 rounded-t-lg cursor-pointer relative group min-h-[4px]"
      >
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition bg-gray-900 text-white text-xs px-3 py-1.5 rounded-lg whitespace-nowrap z-20 shadow-lg font-bold border border-gray-700">
          {actualValue.toLocaleString()} tCO₂e
        </div>
      </motion.div>
      <span className="text-xs text-gray-500 mt-3 font-semibold">{label}</span>
    </motion.div>
  );
};

export default function Dashboard({ tenantId, refreshTrigger }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tenantId) return;
    
    setLoading(true);
    fetch(`${API_BASE_URL}/api/dashboard/summary/?tenant_id=${tenantId}`)
      .then((res) => res.json())
      .then((summary) => {
        setData(summary);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error loading dashboard summary:", err);
        setLoading(false);
      });
  }, [tenantId, refreshTrigger]);

  if (loading || !data) {
    return (
      <section className="py-20 px-6 bg-gradient-to-br from-gray-50 to-white flex flex-col items-center justify-center min-h-[400px]">
        <Loader2 className="w-12 h-12 text-eco-green-500 animate-spin mb-4" />
        <p className="text-gray-500 font-medium animate-pulse">Loading emissions analytics dashboard...</p>
      </section>
    );
  }

  const statCards = [
    {
      label: "Total Records",
      value: data.total_records.toLocaleString(),
      icon: TrendingUp,
      color: "bg-eco-green-500",
    },
    {
      label: "Scope 1 Emissions",
      value: `${data.scope1_emissions.toLocaleString()} tCO₂e`,
      icon: Factory,
      color: "bg-orange-500",
    },
    {
      label: "Scope 2 Emissions",
      value: `${data.scope2_emissions.toLocaleString()} tCO₂e`,
      icon: Zap,
      color: "bg-blue-500",
    },
    {
      label: "Data Quality Rate",
      value: `${data.data_quality}%`,
      icon: CheckCircle,
      color: "bg-eco-green-600",
    },
  ];

  const trend = data.trend || [];
  const maxTrendVal = Math.max(...trend.map((t) => t.value), 1);

  const scopes = [
    { label: "Scope 1 (Direct)", percent: data.scopes.scope1, color: "from-orange-400 to-orange-600" },
    { label: "Scope 2 (Indirect Grid)", percent: data.scopes.scope2, color: "from-blue-400 to-blue-600" },
    { label: "Scope 3 (Value Chain / Travel)", percent: data.scopes.scope3, color: "from-red-400 to-red-600" },
  ];

  return (
    <motion.section
      id="dashboard"
      className="py-20 px-6 bg-gradient-to-br from-gray-50 via-white to-blue-50 border-b border-gray-100"
    >
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mb-12"
        >
          <h2 className="text-4xl font-bold text-gray-900 mb-3">
            Emissions Dashboard
          </h2>
          <p className="text-gray-600 text-lg">
            Real-time calculations, scope distributions, and audit status overview.
          </p>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {statCards.map((stat, idx) => (
            <StatCard
              key={idx}
              label={stat.label}
              value={stat.value}
              icon={stat.icon}
              color={stat.color}
              delay={idx * 0.1}
            />
          ))}
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Emissions Trend Chart */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="lg:col-span-2 bg-white rounded-xl shadow-lg p-8 border border-gray-100 flex flex-col justify-between"
          >
            <div className="mb-6">
              <h3 className="text-xl font-bold text-gray-900">
                Emissions Trend
              </h3>
              <p className="text-gray-500 text-sm mt-1">
                Monthly carbon emissions over the past year (tCO₂e)
              </p>
            </div>
            
            {trend.length === 0 ? (
              <div className="h-72 flex items-center justify-center border border-dashed border-gray-200 rounded-lg text-gray-400 font-medium">
                No data ingested yet. Upload an SAP, Utility, or Travel file to populate trend data.
              </div>
            ) : (
              <div className="h-72 flex items-end justify-between gap-3 px-2">
                {trend.map((month, idx) => {
                  const pctHeight = (month.value / maxTrendVal) * 100;
                  return (
                    <AnimatedBar
                      key={idx}
                      pctHeight={pctHeight}
                      actualValue={month.value}
                      label={month.label}
                      delay={idx * 0.04}
                    />
                  );
                })}
              </div>
            )}
          </motion.div>

          {/* Emissions by Scope */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="bg-white rounded-xl shadow-lg p-8 border border-gray-100 flex flex-col justify-between"
          >
            <div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">
                Emissions by Scope
              </h3>
              <p className="text-gray-500 text-sm mb-8">Distribution breakdown of active records</p>
              
              <div className="space-y-6">
                {scopes.map((scope, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: idx * 0.1 }}
                  >
                    <div className="flex justify-between mb-2 items-center">
                      <span className="text-sm font-semibold text-gray-700">
                        {scope.label}
                      </span>
                      <motion.span
                        initial={{ scale: 0 }}
                        whileInView={{ scale: 1 }}
                        viewport={{ once: true }}
                        transition={{ delay: idx * 0.1 + 0.2 }}
                        className="text-lg font-bold text-gray-900"
                      >
                        {scope.percent}%
                      </motion.span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        whileInView={{ width: `${scope.percent}%` }}
                        viewport={{ once: true }}
                        transition={{ delay: idx * 0.1 + 0.1, duration: 0.8 }}
                        className={`h-full rounded-full bg-gradient-to-r ${scope.color}`}
                      />
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Recommendation Box */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3 }}
              className="mt-8 p-4 bg-blue-50 rounded-xl border border-blue-200"
            >
              <p className="text-xs text-blue-900 font-semibold leading-relaxed">
                💡 Analyst Recommendation: Focus audits on Scope 2 billing periods. These represent the highest density of manual input records.
              </p>
            </motion.div>
          </motion.div>
        </div>
      </div>
    </motion.section>
  );
}
