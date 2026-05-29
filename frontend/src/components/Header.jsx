import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, Leaf, Shield, User, PlusCircle, Check, Loader2 } from "lucide-react";

export default function Header({ tenant, setTenant }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showSignIn, setShowSignIn] = useState(false);
  const [tenantsList, setTenantsList] = useState([]);
  const [loadingTenants, setLoadingTenants] = useState(false);
  const [newTenantName, setNewTenantName] = useState("");
  const [creatingTenant, setCreatingTenant] = useState(false);

  const navItems = [
    { label: "Upload Stream", href: "#upload" },
    { label: "Emissions Dashboard", href: "#dashboard" },
    { label: "Review & Validate", href: "#review" },
  ];

  // Fetch all tenants when sign-in modal is opened
  useEffect(() => {
    if (showSignIn) {
      loadTenants();
    }
  }, [showSignIn]);

  const loadTenants = () => {
    setLoadingTenants(true);
    fetch("http://127.0.0.1:8000/api/tenants/")
      .then((res) => res.json())
      .then((data) => {
        setTenantsList(data);
        setLoadingTenants(false);
      })
      .catch((err) => {
        console.error("Error loading tenants list:", err);
        setLoadingTenants(false);
      });
  };

  const handleCreateTenant = (e) => {
    e.preventDefault();
    if (!newTenantName.trim()) return;

    setCreatingTenant(true);
    fetch("http://127.0.0.1:8000/api/tenants/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name: newTenantName }),
    })
      .then(async (res) => {
        const data = await res.json();
        setCreatingTenant(false);
        if (res.ok) {
          setNewTenantName("");
          // Refresh list and set active tenant
          setTenant(data);
          loadTenants();
        } else {
          alert(data.name ? `Error: ${data.name[0]}` : "Failed to create tenant.");
        }
      })
      .catch((err) => {
        setCreatingTenant(false);
        alert("Failed to reach tenant creation server.");
      });
  };

  const containerVariants = {
    hidden: { opacity: 0, y: -20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6, ease: "easeOut" },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, x: -20 },
    visible: (i) => ({
      opacity: 1,
      x: 0,
      transition: { delay: i * 0.05, duration: 0.5 },
    }),
  };

  return (
    <motion.header
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="bg-gradient-to-r from-eco-green-700 via-eco-green-600 to-blue-700 text-white shadow-2xl sticky top-0 z-50 backdrop-blur-sm bg-opacity-95 border-b border-white/10"
    >
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <motion.div
            className="flex items-center gap-3 cursor-pointer group"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          >
            <motion.div
              className="w-11 h-11 rounded-xl bg-white/20 backdrop-blur-md flex items-center justify-center font-bold border border-white/30 group-hover:bg-white/30 transition"
              whileHover={{ rotate: 15 }}
            >
              <Leaf className="w-5 h-5 text-white" />
            </motion.div>
            <div>
              <h1 className="text-xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-white to-blue-100 leading-tight">
                Breathe ESG
              </h1>
              <p className="text-eco-green-100 text-[10px] font-bold uppercase tracking-wider">
                Emissions Intelligence
              </p>
            </div>
          </motion.div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex gap-8 items-center">
            {navItems.map((item, i) => (
              <motion.a
                key={item.label}
                href={item.href}
                custom={i}
                variants={itemVariants}
                initial="hidden"
                animate="visible"
                className="text-white/95 hover:text-white font-bold text-sm transition-colors relative py-1 group"
              >
                {item.label}
                <span className="absolute bottom-0 left-0 w-0 h-[2px] bg-white group-hover:w-full transition-all duration-300" />
              </motion.a>
            ))}
            
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowSignIn(true)}
              className="px-5 py-2.5 bg-white text-eco-green-700 rounded-xl font-bold text-sm hover:bg-eco-green-50 transition-colors shadow-md flex items-center gap-1.5 cursor-pointer"
            >
              <User className="w-4 h-4" />
              {tenant ? tenant.name : "Sign In"}
            </motion.button>
          </nav>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden text-white"
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Menu */}
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{
            opacity: mobileMenuOpen ? 1 : 0,
            height: mobileMenuOpen ? "auto" : 0,
            marginTop: mobileMenuOpen ? 16 : 0,
          }}
          className="md:hidden overflow-hidden"
        >
          <div className="flex flex-col gap-3 pt-4 border-t border-white/20">
            {navItems.map((item) => (
              <a
                key={item.label}
                href={item.href}
                className="text-white/90 hover:text-white font-bold transition-colors py-2 text-sm"
                onClick={() => setMobileMenuOpen(false)}
              >
                {item.label}
              </a>
            ))}
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                setShowSignIn(true);
              }}
              className="w-full text-center px-5 py-3 bg-white text-eco-green-700 rounded-xl font-bold text-sm shadow-md flex items-center justify-center gap-1.5 mt-2"
            >
              <User className="w-4 h-4" />
              {tenant ? tenant.name : "Sign In"}
            </button>
          </div>
        </motion.div>
      </div>

      {/* Organization Portal / Sign In Modal */}
      <AnimatePresence>
        {showSignIn && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowSignIn(false)}
            className="fixed inset-0 bg-black/45 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-3xl shadow-2xl max-w-md w-full border border-gray-200 overflow-hidden text-gray-900"
            >
              {/* Modal Header */}
              <div className="bg-gradient-to-r from-eco-green-50 to-blue-50 px-6 py-5 border-b border-gray-200 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-eco-green-600" />
                  <h3 className="text-lg font-bold text-gray-900">Organization Access Portal</h3>
                </div>
                <button
                  onClick={() => setShowSignIn(false)}
                  className="text-gray-400 hover:text-gray-600 text-2xl font-light cursor-pointer"
                >
                  ×
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-6 space-y-6">
                <div>
                  <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">
                    Active Organization Scope
                  </h4>
                  {tenant ? (
                    <div className="p-4 bg-eco-green-50 border border-eco-green-200 rounded-xl flex items-center justify-between">
                      <div>
                        <p className="font-bold text-eco-green-900 text-sm">{tenant.name}</p>
                        <p className="text-[10px] text-eco-green-600 font-mono mt-0.5">{tenant.id}</p>
                      </div>
                      <span className="px-2 py-0.5 bg-eco-green-200 text-eco-green-800 text-[10px] font-bold uppercase rounded-full">
                        Active
                      </span>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 italic">No organization selected.</p>
                  )}
                </div>

                {/* Tenant List */}
                <div>
                  <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">
                    Switch Organization Scope
                  </h4>
                  {loadingTenants ? (
                    <div className="py-8 flex justify-center items-center">
                      <Loader2 className="w-6 h-6 text-eco-green-500 animate-spin" />
                    </div>
                  ) : (
                    <div className="max-h-[160px] overflow-y-auto space-y-2 pr-1">
                      {tenantsList.map((t) => (
                        <button
                          key={t.id}
                          onClick={() => {
                            setTenant(t);
                            setShowSignIn(false);
                          }}
                          className={`w-full p-3 rounded-xl border text-left text-sm font-semibold transition flex items-center justify-between ${
                            tenant && tenant.id === t.id
                              ? "bg-eco-green-50/50 border-eco-green-400 text-eco-green-900"
                              : "border-gray-200 hover:bg-gray-50 text-gray-700"
                          }`}
                        >
                          <span className="truncate">{t.name}</span>
                          {tenant && tenant.id === t.id && (
                            <Check className="w-4 h-4 text-eco-green-600 flex-shrink-0" />
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Create Tenant Form */}
                <form onSubmit={handleCreateTenant} className="border-t border-gray-100 pt-5 space-y-3">
                  <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1">
                    <PlusCircle className="w-4 h-4 text-gray-400" />
                    Onboard New Organization
                  </h4>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newTenantName}
                      onChange={(e) => setNewTenantName(e.target.value)}
                      placeholder="e.g. Acme Manufacturing"
                      className="flex-1 border border-gray-300 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-eco-green-500 focus:border-transparent outline-none transition"
                      disabled={creatingTenant}
                    />
                    <button
                      type="submit"
                      disabled={creatingTenant || !newTenantName.trim()}
                      className="px-4 py-2 bg-eco-green-600 text-white rounded-xl font-bold text-sm hover:bg-eco-green-700 transition disabled:opacity-50 flex items-center gap-1 cursor-pointer"
                    >
                      {creatingTenant ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        "Onboard"
                      )}
                    </button>
                  </div>
                </form>
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 text-center">
                <button
                  onClick={() => setShowSignIn(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 bg-white rounded-xl text-xs font-bold hover:bg-gray-50 transition cursor-pointer"
                >
                  Close Scope Portal
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
