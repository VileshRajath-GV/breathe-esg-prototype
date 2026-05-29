import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Header from "./components/Header";
import FileUpload from "./components/FileUpload";
import Dashboard from "./components/Dashboard";
import ReviewPanel from "./components/ReviewPanel";
import Footer from "./components/Footer";
import { ArrowRight, Zap, Info, FileText, CheckCircle, ShieldAlert } from "lucide-react";
import { API_BASE_URL } from "./config";

export default function App() {
  const [tenant, setTenant] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    // Dynamically fetch the first tenant seeded in the database
    fetch(`${API_BASE_URL}/api/tenants/`)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.length > 0) {
          setTenant(data[0]);
        }
      })
      .catch((err) => console.error("Error fetching default tenant:", err));
  }, []);

  const handleUploadSuccess = () => {
    // Trigger dashboard and review panel reload
    setRefreshTrigger((prev) => prev + 1);
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.8, ease: "easeOut" },
    },
  };

  return (
    <div className="w-full min-h-screen bg-white overflow-hidden">
      <Header tenant={tenant} setTenant={setTenant} />

      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-eco-green-50 via-blue-50 to-purple-50 py-24 px-6 overflow-hidden">
        {/* Animated background shapes */}
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
            rotate: [0, 180, 360],
          }}
          transition={{ duration: 20, repeat: Infinity }}
          className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-eco-green-200 to-blue-200 rounded-full mix-blend-multiply filter blur-3xl opacity-20"
        />
        <motion.div
          animate={{
            scale: [1.1, 1, 1.1],
            rotate: [360, 180, 0],
          }}
          transition={{ duration: 20, repeat: Infinity }}
          className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-br from-blue-200 to-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-20"
        />

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="max-w-7xl mx-auto text-center relative z-10"
        >
          <motion.div variants={itemVariants} className="inline-block mb-6">
            <span className="px-4 py-2 bg-eco-green-100 text-eco-green-700 rounded-full text-sm font-bold inline-flex items-center gap-2 border border-eco-green-200">
              <Zap className="w-4 h-4" />
              Powered by Advanced Analytics
            </span>
          </motion.div>

          <motion.h2
            variants={itemVariants}
            className="text-6xl md:text-7xl font-bold text-gray-900 mb-6 leading-tight"
          >
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-eco-green-600 via-blue-600 to-purple-600">
              Streamline Your ESG Emissions
            </span>
            <br />
            Reporting
          </motion.h2>

          <motion.p
            variants={itemVariants}
            className="text-xl md:text-2xl text-gray-600 max-w-3xl mx-auto mb-8 leading-relaxed"
          >
            Upload, normalize, and review emissions data with confidence.
            Transform raw data into actionable ESG insights powered by AI.
          </motion.p>

          <motion.div
            variants={itemVariants}
            className="flex flex-col sm:flex-row gap-4 justify-center items-center"
          >
            <motion.a
              href="#upload"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-8 py-4 bg-gradient-to-r from-eco-green-600 to-eco-green-500 text-white rounded-xl font-bold text-lg shadow-lg hover:shadow-xl transition flex items-center gap-2"
            >
              Get Started
              <ArrowRight className="w-5 h-5" />
            </motion.a>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowHelp(true)}
              className="px-8 py-4 bg-white text-eco-green-600 border-2 border-eco-green-600 rounded-xl font-bold text-lg hover:bg-eco-green-50 transition cursor-pointer"
            >
              Learn More
            </motion.button>
          </motion.div>

          {/* Active Tenant Badge */}
          {tenant && (
            <motion.div variants={itemVariants} className="mt-8">
              <span className="px-4 py-2 bg-blue-100 text-blue-800 rounded-full text-xs font-semibold border border-blue-200">
                Active Organization Scope: <strong>{tenant.name}</strong>
              </span>
            </motion.div>
          )}

          {/* Stats */}
          <motion.div
            variants={itemVariants}
            className="grid grid-cols-3 md:grid-cols-3 gap-8 mt-16 pt-12 border-t border-gray-200"
          >
            {[
              { label: "Data Processed", value: "2.8M+", icon: "📊" },
              { label: "Accuracy Rate", value: "98.5%", icon: "✓" },
              { label: "Users Active", value: "1000+", icon: "👥" },
            ].map((stat, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1 + idx * 0.2 }}
              >
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                <p className="text-gray-600 text-sm mt-1">{stat.label}</p>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      <FileUpload tenantId={tenant?.id} onUploadSuccess={handleUploadSuccess} />
      <Dashboard tenantId={tenant?.id} refreshTrigger={refreshTrigger} />
      <ReviewPanel tenantId={tenant?.id} refreshTrigger={refreshTrigger} />
      <Footer />

      {/* Learn More / Operations Manual Modal */}
      <AnimatePresence>
        {showHelp && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowHelp(false)}
            className="fixed inset-0 bg-black/45 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-3xl shadow-2xl max-w-3xl w-full border border-gray-200 overflow-hidden text-gray-900"
            >
              {/* Modal Header */}
              <div className="bg-gradient-to-r from-eco-green-50 to-blue-50 px-8 py-5 border-b border-gray-200 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <Info className="w-5 h-5 text-eco-green-600" />
                  <h3 className="text-xl font-bold text-gray-900">Breathe ESG - Operations Manual</h3>
                </div>
                <button
                  onClick={() => setShowHelp(false)}
                  className="text-gray-400 hover:text-gray-600 text-3xl font-light cursor-pointer"
                >
                  ×
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-8 space-y-6 max-h-[60vh] overflow-y-auto">
                <div>
                  <h4 className="text-sm font-bold text-eco-green-700 uppercase tracking-wider mb-2">
                    1. Overview
                  </h4>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    Breathe ESG Ingestion & Reporting platform simplifies carbon accounting by taking messy, unstructured data directly from core enterprise exports, dynamically normalizing them, performing greenhouse gas emission calculations, and providing an immutable audit trail ledger.
                  </p>
                </div>

                <div className="border-t border-gray-100 pt-5">
                  <h4 className="text-sm font-bold text-eco-green-700 uppercase tracking-wider mb-2">
                    2. Ingesting Raw Client Streams
                  </h4>
                  <p className="text-sm text-gray-600 leading-relaxed mb-3">
                    Sustainability analysts can drop files directly into our upload stream. Ready-to-use testing files are available in the GitHub repository:
                  </p>
                  <div className="p-4 bg-gray-50 border border-gray-200 rounded-2xl text-xs space-y-2">
                    <p className="font-semibold text-gray-800">📁 Sample Files on GitHub:</p>
                    <a
                      href="https://github.com/VileshRajath-GV/breathe-esg-prototype/tree/main/sample_files"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block bg-white p-2 border border-gray-300 rounded font-mono text-[11px] text-blue-700 hover:text-blue-900 hover:underline break-all"
                    >
                      github.com/VileshRajath-GV/breathe-esg-prototype/tree/main/sample_files
                    </a>
                    <ul className="list-disc pl-5 space-y-1 mt-2 text-gray-500 font-semibold">
                      <li><strong>SAP ECC Fuel CSV</strong>: Simulates legacy ERP transaction data with German technical column names (`WERKS`, `MENGE`, etc.) and localized date formatting.</li>
                      <li><strong>Utility Electricity CSV</strong>: Mimics portal billing downloads with overlapping days that cross calendar months.</li>
                      <li><strong>Corporate Travel JSON</strong>: Mimics navan/concur flight booking records containing airport codes but lacking explicit distance metrics.</li>
                    </ul>
                  </div>
                </div>

                <div className="border-t border-gray-100 pt-5">
                  <h4 className="text-sm font-bold text-eco-green-700 uppercase tracking-wider mb-2">
                    3. Under the Hood: Calculation Calculations
                  </h4>
                  <div className="grid grid-cols-3 gap-4 text-xs font-semibold">
                    <div className="p-4 bg-orange-50 border border-orange-200 rounded-xl">
                      <p className="text-orange-950 font-bold uppercase tracking-wide mb-1">Scope 1 (Direct)</p>
                      <p className="text-gray-500 leading-relaxed font-medium">Stationary combustion. Multiplies fuel liters/gallons by specific density combustion factor (e.g. diesel $\rightarrow$ 0.00268 tCO2e/L).</p>
                    </div>
                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
                      <p className="text-blue-950 font-bold uppercase tracking-wide mb-1">Scope 2 (Electricity)</p>
                      <p className="text-gray-500 leading-relaxed font-medium">Indirect grid energy. Splits billing periods daily, allocates matching usage to calendar months, and multiplies by grid subfactors.</p>
                    </div>
                    <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
                      <p className="text-red-950 font-bold uppercase tracking-wide mb-1">Scope 3 (Travel)</p>
                      <p className="text-gray-500 leading-relaxed font-medium">Business flights. Runs Great-Circle Haversine calculations between airport codes, applying cabin class multipliers.</p>
                    </div>
                  </div>
                </div>

                <div className="border-t border-gray-100 pt-5">
                  <h4 className="text-sm font-bold text-eco-green-700 uppercase tracking-wider mb-2">
                    4. Auditor-Immune Lock State
                  </h4>
                  <p className="text-sm text-gray-600 leading-relaxed">
                    Exposing raw payloads inside details modal prevents auditor "black-box" skepticism. Once an analyst signs off and clicks <strong>Approve & Lock</strong>, the record becomes 100% database-locked. Further programmatic edits or deletions are blocked, satisfying regulatory audit trail requirements.
                  </p>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="px-8 py-5 bg-gray-50 border-t border-gray-200 flex justify-between items-center">
                <a
                  href="https://github.com/VileshRajath-GV/breathe-esg-prototype"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs text-eco-green-600 hover:text-eco-green-800 font-extrabold"
                >
                  <FileText className="w-4 h-4" />
                  View Project on GitHub
                </a>
                <button
                  onClick={() => setShowHelp(false)}
                  className="px-6 py-2.5 bg-white border border-gray-300 text-gray-700 rounded-xl text-xs font-bold hover:bg-gray-50 transition cursor-pointer"
                >
                  Close Manual
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
