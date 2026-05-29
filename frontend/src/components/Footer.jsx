import { motion } from "framer-motion";
import { Leaf, Code2, Heart, MessageSquare } from "lucide-react";

export default function Footer() {
  const footerLinks = {
    Product: ["Features", "Pricing", "Documentation", "API"],
    Company: ["About", "Blog", "Careers", "Contact"],
    Legal: ["Privacy", "Terms", "Security", "Compliance"],
    Resources: ["Guides", "Templates", "Community", "Support"],
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
  };

  return (
    <motion.footer
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.8 }}
      className="bg-gradient-to-b from-gray-900 via-gray-900 to-black text-white py-16 px-6 mt-16 relative overflow-hidden"
    >
      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-eco-green-600/10 via-transparent to-blue-600/10 pointer-events-none" />

      <div className="max-w-7xl mx-auto relative z-10">
        {/* Top Section */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 mb-12 pb-12 border-b border-gray-800"
        >
          {/* Brand */}
          <motion.div variants={itemVariants} className="lg:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-2 bg-gradient-to-br from-eco-green-500 to-blue-500 rounded-lg">
                <Leaf className="w-5 h-5 text-white" />
              </div>
              <h3 className="font-bold text-xl bg-clip-text text-transparent bg-gradient-to-r from-eco-green-400 to-blue-400">
                Breathe ESG
              </h3>
            </div>
            <p className="text-gray-400 text-sm leading-relaxed">
              Leading emissions intelligence platform for sustainable
              enterprises.
            </p>
            <div className="flex gap-4 mt-6">
              {[
                { icon: Code2, label: "GitHub" },
                { icon: Heart, label: "LinkedIn" },
                { icon: MessageSquare, label: "Twitter" },
              ].map((social) => (
                <motion.a
                  key={social.label}
                  href="#"
                  whileHover={{ scale: 1.1, y: -3 }}
                  whileTap={{ scale: 0.95 }}
                  className="p-2 rounded-lg bg-gray-800 hover:bg-eco-green-600 transition duration-300"
                  title={social.label}
                >
                  <social.icon className="w-5 h-5" />
                </motion.a>
              ))}
            </div>
          </motion.div>

          {/* Links */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <motion.div key={category} variants={itemVariants}>
              <h4 className="font-bold text-white mb-4 flex items-center gap-2">
                <span className="w-1 h-4 bg-gradient-to-b from-eco-green-500 to-blue-500 rounded" />
                {category}
              </h4>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link}>
                    <motion.a
                      href="#"
                      whileHover={{ x: 5 }}
                      className="text-gray-400 hover:text-white transition duration-300 text-sm"
                    >
                      {link}
                    </motion.a>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </motion.div>

        {/* Bottom Section */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="flex flex-col md:flex-row justify-between items-center pt-8"
        >
          <motion.p variants={itemVariants} className="text-gray-400 text-sm">
            © 2026 Breathe ESG. All rights reserved. Built with{" "}
            <span className="text-eco-green-400">💚</span>
          </motion.p>
          <motion.div
            variants={itemVariants}
            className="flex gap-6 mt-4 md:mt-0"
          >
            <a
              href="#"
              className="text-gray-400 hover:text-white text-sm transition"
            >
              Status
            </a>
            <span className="text-gray-700">•</span>
            <a
              href="#"
              className="text-gray-400 hover:text-white text-sm transition"
            >
              Changelog
            </a>
            <span className="text-gray-700">•</span>
            <a
              href="#"
              className="text-gray-400 hover:text-white text-sm transition"
            >
              Credits
            </a>
          </motion.div>
        </motion.div>
      </div>

      {/* Animated background element */}
      <motion.div
        animate={{
          scale: [1, 1.2, 1],
          rotate: [0, 90, 180],
        }}
        transition={{ duration: 20, repeat: Infinity }}
        className="absolute bottom-0 right-0 w-96 h-96 bg-gradient-to-br from-eco-green-500/5 to-blue-500/5 rounded-full blur-3xl pointer-events-none"
      />
    </motion.footer>
  );
}
