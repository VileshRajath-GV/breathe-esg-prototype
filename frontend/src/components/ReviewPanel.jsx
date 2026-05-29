import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle,
  AlertCircle,
  XCircle,
  ChevronDown,
  FileCheck,
  Calendar,
  Flag,
  Zap,
  Loader2,
  FileCode,
} from "lucide-react";
import { API_BASE_URL } from "../config";

export default function ReviewPanel({ tenantId, refreshTrigger }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("all");
  const [localRefresh, setLocalRefresh] = useState(0);

  // Modal and Action States
  const [showModal, setShowModal] = useState(false);
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [actionComment, setActionComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!tenantId) return;

    setLoading(true);
    fetch(`${API_BASE_URL}/api/records/?tenant_id=${tenantId}&status=${filterStatus}`)
      .then((res) => res.json())
      .then((data) => {
        setRecords(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error loading records:", err);
        setLoading(false);
      });
  }, [tenantId, filterStatus, refreshTrigger, localRefresh]);

  const getStatusIcon = (statusVal) => {
    switch (statusVal) {
      case "validated":
        return <CheckCircle className="w-5 h-5 text-eco-green-600" />;
      case "review":
        return <AlertCircle className="w-5 h-5 text-yellow-600" />;
      case "error":
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (statusVal) => {
    switch (statusVal) {
      case "validated":
        return "bg-eco-green-100 text-eco-green-800 border-eco-green-300";
      case "review":
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
      case "error":
        return "bg-red-100 text-red-800 border-red-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  const handleRowClick = (record) => {
    setSelectedDetail(record);
    setActionComment("");
    setShowModal(true);
  };

  const handleApprove = () => {
    if (!selectedDetail) return;
    setIsSubmitting(true);

    fetch(`${API_BASE_URL}/api/records/${selectedDetail.id}/approve/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        comment: actionComment || "Analyst approved and locked this record.",
        performed_by: "Sustainability Analyst",
      }),
    })
      .then(async (res) => {
        const data = await res.json();
        setIsSubmitting(false);
        if (res.ok) {
          setShowModal(false);
          setLocalRefresh((prev) => prev + 1);
        } else {
          alert(data.error || "Approval failed.");
        }
      })
      .catch((err) => {
        setIsSubmitting(false);
        alert("Failed to submit approval.");
      });
  };

  const handleFlag = (statusVal) => {
    if (!selectedDetail) return;
    if (actionComment.trim() === "") {
      alert("Please provide an audit comment explaining why this record is being flagged.");
      return;
    }
    setIsSubmitting(true);

    fetch(`${API_BASE_URL}/api/records/${selectedDetail.id}/flag/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        status: statusVal,
        comment: actionComment,
        performed_by: "Sustainability Analyst",
      }),
    })
      .then(async (res) => {
        const data = await res.json();
        setIsSubmitting(false);
        if (res.ok) {
          setShowModal(false);
          setLocalRefresh((prev) => prev + 1);
        } else {
          alert(data.error || "Flagging failed.");
        }
      })
      .catch((err) => {
        setIsSubmitting(false);
        alert("Failed to submit flag.");
      });
  };

  const filters = [
    { key: "all", label: "All Records", color: "eco-green" },
    { key: "validated", label: "✓ Validated", color: "eco-green" },
    { key: "review", label: "⚠ Review Needed", color: "yellow" },
    { key: "error", label: "✗ Errors", color: "red" },
  ];

  return (
    <motion.section
      id="review"
      className="py-20 px-6 bg-gradient-to-br from-white via-gray-50 to-gray-100 min-h-[500px]"
    >
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mb-12"
        >
          <h2 className="text-4xl font-bold text-gray-900 mb-3">
            Review & Validate Data
          </h2>
          <p className="text-gray-600 text-lg">
            Inspect raw inputs, evaluate calculation quality scores, and lock approved rows for audit trails.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-200"
        >
          {/* Filter Bar */}
          <div className="border-b border-gray-200 p-6 flex flex-wrap gap-3 bg-gradient-to-r from-gray-50 to-white justify-between items-center">
            <div className="flex gap-3">
              {filters.map((filter) => (
                <button
                  key={filter.key}
                  onClick={() => setFilterStatus(filter.key)}
                  className={`px-5 py-2.5 rounded-lg font-bold text-sm transition border-2 ${
                    filterStatus === filter.key
                      ? "bg-eco-green-600 text-white border-eco-green-600 shadow-md"
                      : "bg-gray-100 text-gray-700 border-transparent hover:bg-gray-200"
                  }`}
                >
                  {filter.label}
                </button>
              ))}
            </div>
            <div className="text-sm font-semibold text-gray-500">
              Found {records.length} records
            </div>
          </div>

          {/* Table / Content */}
          {loading ? (
            <div className="py-20 text-center flex flex-col items-center justify-center">
              <Loader2 className="w-10 h-10 text-eco-green-500 animate-spin mb-3" />
              <p className="text-gray-500 font-medium">Filtering ESG records...</p>
            </div>
          ) : records.length === 0 ? (
            <div className="py-20 text-center text-gray-400 font-semibold">
              No emissions records match your current filter criteria.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-100 border-b border-gray-200">
                  <tr>
                    {[
                      "Facility Name",
                      "Emissions Scope",
                      "Activity / Fuel",
                      "Normalized Value",
                      "Confidence",
                      "Status",
                      "Action",
                    ].map((header) => (
                      <th
                        key={header}
                        className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider"
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence>
                    {records.map((row, idx) => (
                      <motion.tr
                        key={row.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        transition={{ delay: Math.min(idx * 0.03, 0.5) }}
                        onClick={() => handleRowClick(row)}
                        className="border-b border-gray-200 hover:bg-gradient-to-r hover:from-eco-green-50/50 hover:to-blue-50/50 transition cursor-pointer group"
                      >
                        <td className="px-6 py-4 font-bold text-gray-900 group-hover:text-eco-green-700">
                          {row.facility}
                        </td>
                        <td className="px-6 py-4 text-gray-600 text-sm font-semibold">
                          {row.scope}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500">
                          {row.activity_type}
                        </td>
                        <td className="px-6 py-4 font-extrabold text-gray-900">
                          {parseFloat(row.normalized_value_tco2e).toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 4,
                          })}{" "}
                          tCO₂e
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <div className="w-16 bg-gray-200 rounded-full h-2 overflow-hidden">
                              <div
                                className="h-full bg-gradient-to-r from-eco-green-400 to-eco-green-600 rounded-full"
                                style={{ width: `${row.confidence_score}%` }}
                              />
                            </div>
                            <span className="text-xs font-bold text-gray-700 min-w-fit">
                              {row.confidence_score}%
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            {getStatusIcon(row.status)}
                            <span
                              className={`px-3 py-1 rounded-full text-xs font-bold border uppercase tracking-wider ${getStatusColor(
                                row.status
                              )}`}
                            >
                              {row.status === "validated" && "Validated"}
                              {row.status === "review" && "Review"}
                              {row.status === "error" && "Error"}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <motion.button
                            whileHover={{ x: 3 }}
                            className="text-eco-green-600 hover:text-eco-green-800 font-bold flex items-center gap-1 text-sm"
                          >
                            Details
                            <ChevronDown className="w-4 h-4" />
                          </motion.button>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      </div>

      {/* Modal Detail View */}
      <AnimatePresence>
        {showModal && selectedDetail && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowModal(false)}
            className="fixed inset-0 bg-black/45 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-3xl shadow-2xl max-w-3xl w-full border border-gray-200 overflow-hidden"
            >
              {/* Modal Header */}
              <div className="bg-gradient-to-r from-eco-green-50 to-blue-50 px-8 py-6 border-b border-gray-200 flex justify-between items-start">
                <div>
                  <h3 className="text-2xl font-bold text-gray-900">
                    {selectedDetail.facility}
                  </h3>
                  <p className="text-gray-600 mt-1 font-semibold flex items-center gap-2">
                    <span className="px-2.5 py-0.5 bg-white/80 border border-gray-200 rounded text-xs">
                      {selectedDetail.scope}
                    </span>
                    <span>{selectedDetail.category}</span>
                  </p>
                </div>
                <button
                  onClick={() => setShowModal(false)}
                  className="text-gray-400 hover:text-gray-700 text-3xl font-light cursor-pointer"
                >
                  ×
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-8 space-y-6 max-h-[60vh] overflow-y-auto">
                <div className="grid grid-cols-2 gap-6">
                  <div className="p-4 bg-blue-50 rounded-2xl border border-blue-200">
                    <p className="text-xs text-blue-900 font-bold uppercase tracking-wider mb-1">
                      Calculated Carbon Emissions
                    </p>
                    <p className="text-3xl font-extrabold text-gray-900">
                      {parseFloat(selectedDetail.normalized_value_tco2e).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 6,
                      })}
                    </p>
                    <p className="text-xs text-gray-500 mt-1 font-bold">tonnes of CO₂ equivalent (tCO₂e)</p>
                  </div>

                  <div className="p-4 bg-eco-green-50 rounded-2xl border border-eco-green-200">
                    <p className="text-xs text-eco-green-900 font-bold uppercase tracking-wider mb-1">
                      Emissions Factor Quality
                    </p>
                    <p className="text-3xl font-extrabold text-eco-green-700">
                      {selectedDetail.confidence_score}%
                    </p>
                    <div className="w-full bg-gray-300 rounded-full h-2 mt-3 overflow-hidden">
                      <div
                        className="h-full bg-eco-green-500 rounded-full"
                        style={{ width: `${selectedDetail.confidence_score}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Audit & Dates Metadata */}
                <div className="grid grid-cols-3 gap-4 p-5 bg-gray-50 border border-gray-200 rounded-2xl text-sm">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white border border-gray-200 rounded-xl">
                      <Calendar className="w-5 h-5 text-gray-600" />
                    </div>
                    <div>
                      <p className="text-[10px] text-gray-400 font-bold uppercase">Occurred Date</p>
                      <p className="font-bold text-gray-800">
                        {selectedDetail.transaction_date}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white border border-gray-200 rounded-xl">
                      <FileCheck className="w-5 h-5 text-gray-600" />
                    </div>
                    <div>
                      <p className="text-[10px] text-gray-400 font-bold uppercase">Audit Lock Status</p>
                      <p className="font-bold text-gray-800">
                        {selectedDetail.is_locked ? "🔒 Locked" : "🔓 Open"}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white border border-gray-200 rounded-xl">
                      <Zap className="w-5 h-5 text-gray-600" />
                    </div>
                    <div>
                      <p className="text-[10px] text-gray-400 font-bold uppercase">Source Stream</p>
                      <p className="font-bold text-gray-800">
                        {selectedDetail.batch_filename ? selectedDetail.batch_filename.split("_")[0] : "Direct API"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Validation warnings / anomalies */}
                <div className="p-4 bg-yellow-50/80 border border-yellow-200 rounded-2xl">
                  <p className="text-xs text-yellow-900 font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
                    <AlertCircle className="w-4 h-4 text-yellow-600" />
                    Calculations Log & Quality Flags
                  </p>
                  <p className="text-gray-700 text-sm font-semibold italic">
                    {selectedDetail.validation_notes || "Ingestion successful. No anomalies flagged."}
                  </p>
                </div>

                {/* Audit Source: Raw Ingested Payload */}
                <div>
                  <h4 className="text-sm font-bold text-gray-900 mb-2 flex items-center gap-1">
                    <FileCode className="w-4 h-4 text-blue-500" />
                    Auditing Ledger: Raw Client Export Row
                  </h4>
                  <div className="bg-gray-950 p-5 rounded-2xl max-h-[150px] overflow-y-auto border border-gray-800">
                    <pre className="text-xs text-eco-green-400 font-mono leading-relaxed whitespace-pre-wrap">
                      {JSON.stringify(selectedDetail.raw_payload, null, 2)}
                    </pre>
                  </div>
                  <p className="text-[10px] text-gray-400 mt-2 italic font-semibold">
                    * The ledger preserves the exact column names, dates, and values directly from the client's original SAP/Utility/Travel upload to satisfy auditor reproducibility checks.
                  </p>
                </div>

                {/* Audit Adjustment Input (Active edit lock checks) */}
                {!selectedDetail.is_locked && (
                  <div className="space-y-2 pt-2">
                    <label className="text-sm font-bold text-gray-700 flex items-center gap-1">
                      <Flag className="w-4 h-4 text-yellow-600" />
                      Auditing Action Comment
                    </label>
                    <textarea
                      value={actionComment}
                      onChange={(e) => setActionComment(e.target.value)}
                      placeholder="Specify your rationale for approval or why this row requires correction (mandatory to Flag)..."
                      className="w-full border border-gray-300 rounded-xl p-3 text-sm focus:ring-2 focus:ring-eco-green-500 focus:border-transparent outline-none transition"
                      rows={2}
                    />
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="px-8 py-6 bg-gray-50 border-t border-gray-200 flex gap-3">
                {selectedDetail.is_locked ? (
                  <div className="flex-1 text-center py-2 bg-eco-green-50 text-eco-green-800 font-bold border border-eco-green-200 rounded-xl text-sm">
                    🔒 This record has been validated and locked for audit. It is immune to editing.
                  </div>
                ) : (
                  <>
                    <button
                      disabled={isSubmitting}
                      onClick={handleApprove}
                      className="flex-1 bg-eco-green-600 text-white px-4 py-3.5 rounded-xl font-bold hover:bg-eco-green-700 transition flex items-center justify-center gap-2 shadow-md cursor-pointer disabled:opacity-50"
                    >
                      {isSubmitting ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <CheckCircle className="w-5 h-5" />
                      )}
                      Approve & Lock for Audit
                    </button>
                    <button
                      disabled={isSubmitting}
                      onClick={() => handleFlag("review")}
                      className="flex-1 bg-yellow-500 text-white px-4 py-3.5 rounded-xl font-bold hover:bg-yellow-600 transition flex items-center justify-center gap-2 shadow-md cursor-pointer disabled:opacity-50"
                    >
                      {isSubmitting ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Flag className="w-5 h-5" />
                      )}
                      Flag for Review
                    </button>
                    <button
                      disabled={isSubmitting}
                      onClick={() => handleFlag("error")}
                      className="flex-1 bg-red-600 text-white px-4 py-3.5 rounded-xl font-bold hover:bg-red-700 transition flex items-center justify-center gap-2 shadow-md cursor-pointer disabled:opacity-50"
                    >
                      {isSubmitting ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <XCircle className="w-5 h-5" />
                      )}
                      Reject as Error
                    </button>
                  </>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  );
}
