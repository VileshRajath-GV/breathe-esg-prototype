import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, File, CheckCircle, AlertCircle, RefreshCw } from "lucide-react";

export default function FileUpload({ tenantId, onUploadSuccess }) {
  const [sourceType, setSourceType] = useState("SAP"); // 'SAP', 'Utility', 'Travel'
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState(null); // 'uploading', 'success', 'error'
  const [errorMessage, setErrorMessage] = useState(null);
  const [fileSize, setFileSize] = useState(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  const handleFile = (file) => {
    // Validate file extensions
    const ext = file.name.split(".").pop().toLowerCase();
    if (sourceType === "Travel" && ext !== "json") {
      setErrorMessage("Corporate Travel platform requires a raw JSON file export.");
      setUploadStatus("error");
      return;
    }
    if ((sourceType === "SAP" || sourceType === "Utility") && ext !== "csv") {
      setErrorMessage(`${sourceType} ingestion requires a standard CSV file export.`);
      setUploadStatus("error");
      return;
    }

    setFileName(file.name);
    setFileSize(formatFileSize(file.size));
    setUploadStatus("uploading");
    setUploadProgress(10);
    setErrorMessage(null);

    // Set progress intervals for UX
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 80) {
          clearInterval(interval);
          return 80;
        }
        return prev + 15;
      });
    }, 150);

    // Form data upload
    const formData = new FormData();
    formData.append("file", file);
    formData.append("source_type", sourceType);
    formData.append("tenant_id", tenantId);

    fetch("http://127.0.0.1:8000/api/ingest/", {
      method: "POST",
      body: formData,
    })
      .then(async (res) => {
        clearInterval(interval);
        const data = await res.json();
        if (res.ok) {
          setUploadProgress(100);
          setTimeout(() => {
            setUploadStatus("success");
            onUploadSuccess();
          }, 300);
        } else {
          setUploadStatus("error");
          setErrorMessage(data.error || data.details || "Inconsistent format detected. Processing failed.");
        }
      })
      .catch((err) => {
        clearInterval(interval);
        setUploadStatus("error");
        setErrorMessage("Network error: Could not reach Django ingestion server.");
      });
  };

  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6, ease: "easeOut" },
    },
  };

  const dropzoneVariants = {
    idle: {
      borderColor: "rgba(200, 200, 200, 0.5)",
      backgroundColor: "rgba(255, 255, 255, 0)",
    },
    dragging: {
      borderColor: "rgb(34, 197, 94)",
      backgroundColor: "rgba(34, 197, 94, 0.05)",
      boxShadow: "0 0 20px rgba(34, 197, 94, 0.1)",
    },
  };

  return (
    <motion.section
      id="upload"
      variants={containerVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true }}
      className="py-20 px-6 bg-gradient-to-br from-gray-50 to-white border-b border-gray-100"
    >
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mb-10 text-center"
        >
          <h2 className="text-4xl font-bold text-gray-900 mb-3">
            Ingest Client Data
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Choose the target data stream, then drag and drop the raw export file to run the normalization engine.
          </p>
        </motion.div>

        {/* Source Stream Selector */}
        <div className="grid grid-cols-3 gap-4 mb-8 bg-gray-100/80 p-2 rounded-2xl border border-gray-200">
          {[
            { id: "SAP", name: "SAP ECC (Fuel & Procurement)", ext: "CSV" },
            { id: "Utility", name: "Utility Portal (Electricity)", ext: "CSV" },
            { id: "Travel", name: "Corporate Travel (Concur)", ext: "JSON" },
          ].map((src) => (
            <button
              key={src.id}
              onClick={() => {
                setSourceType(src.id);
                setUploadStatus(null);
                setFileName(null);
                setErrorMessage(null);
              }}
              className={`py-4 px-4 rounded-xl font-bold text-sm transition flex flex-col items-center gap-1 border-2 ${
                sourceType === src.id
                  ? "bg-white text-eco-green-600 border-eco-green-500 shadow-md"
                  : "text-gray-600 border-transparent hover:bg-white/50"
              }`}
            >
              <span>{src.name}</span>
              <span className="text-xs px-2 py-0.5 bg-gray-200 text-gray-700 font-semibold rounded uppercase">
                .{src.ext} format
              </span>
            </button>
          ))}
        </div>

        {/* Drop Zone */}
        <motion.div
          animate={isDragging ? "dragging" : "idle"}
          variants={dropzoneVariants}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className="border-2 border-dashed rounded-2xl p-16 text-center cursor-pointer transition duration-300 relative overflow-hidden"
        >
          <input
            type="file"
            accept={sourceType === "Travel" ? ".json" : ".csv"}
            onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}
            className="hidden"
            id="file-input"
          />

          <label htmlFor="file-input" className="cursor-pointer block">
            <motion.div animate={{ y: isDragging ? -5 : 0 }} className="mb-6">
              <motion.div
                animate={{ scale: isDragging ? 1.1 : 1 }}
                className="inline-block"
              >
                <Upload
                  className="w-16 h-16 text-eco-green-500 mx-auto"
                  strokeWidth={1.5}
                />
              </motion.div>
            </motion.div>

            <p className="text-2xl font-bold text-gray-900 mb-2">
              {fileName ? fileName : `Drop your raw ${sourceType} export here`}
            </p>
            <p className="text-gray-500 mb-4">
              or click to select from your computer
            </p>
            {fileSize && (
              <p className="text-sm text-gray-500 font-semibold">File size: {fileSize}</p>
            )}
          </label>
        </motion.div>

        {/* Upload Status Panels */}
        <AnimatePresence mode="wait">
          {uploadStatus === "uploading" && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mt-8"
            >
              <div className="flex justify-between items-center mb-3">
                <span className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-eco-green-500" />
                  Running normalization engine & calculating emissions...
                </span>
                <span className="text-sm font-bold text-eco-green-600">
                  {Math.round(uploadProgress)}%
                </span>
              </div>
              <div className="relative h-3 bg-gray-200 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${uploadProgress}%` }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                  className="absolute top-0 left-0 h-full bg-gradient-to-r from-eco-green-400 via-eco-green-500 to-blue-500"
                />
              </div>
            </motion.div>
          )}

          {uploadStatus === "success" && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="mt-8"
            >
              <div className="p-6 bg-gradient-to-r from-eco-green-50 to-blue-50 border border-eco-green-200 rounded-2xl flex items-start gap-4">
                <CheckCircle className="w-8 h-8 text-eco-green-600 flex-shrink-0 mt-1" />
                <div className="flex-1">
                  <p className="font-bold text-eco-green-900 text-lg">
                    Ingestion Successful!
                  </p>
                  <p className="text-eco-green-700 mt-1">
                    Normalized and verified emissions records have been registered under your Organization Scope. Check the dashboard and review panel below.
                  </p>
                </div>
              </div>
            </motion.div>
          )}

          {uploadStatus === "error" && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="mt-8"
            >
              <div className="p-6 bg-red-50 border border-red-200 rounded-2xl flex items-start gap-4">
                <AlertCircle className="w-8 h-8 text-red-600 flex-shrink-0 mt-1" />
                <div className="flex-1">
                  <p className="font-bold text-red-900 text-lg">
                    Validation / Ingestion Error
                  </p>
                  <p className="text-red-700 mt-1 font-medium">
                    {errorMessage}
                  </p>
                  <p className="text-xs text-red-500 mt-2 font-mono">
                    Ensure columns, date types, and units conform to requirements.
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.section>
  );
}
