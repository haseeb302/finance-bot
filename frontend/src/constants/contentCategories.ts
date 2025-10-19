/**
 * Content categories for the FinanceBot knowledge base
 * These categories help organize and tag chat conversations
 */
export enum ContentCategory {
  ACCOUNT_REGISTRATION = "account_registration",
  PAYMENTS_TRANSACTIONS = "payments_transactions",
  SECURITY_FRAUD_PREVENTION = "security_fraud_prevention",
  REGULATIONS_COMPLIANCE = "regulations_compliance",
  TECHNICAL_SUPPORT = "technical_support",
  GENERAL = "general",
}

/**
 * Display names for content categories
 */
export const CONTENT_CATEGORY_LABELS: Record<ContentCategory, string> = {
  [ContentCategory.ACCOUNT_REGISTRATION]: "Account & Registration",
  [ContentCategory.PAYMENTS_TRANSACTIONS]: "Payments & Transactions",
  [ContentCategory.SECURITY_FRAUD_PREVENTION]: "Security & Fraud Prevention",
  [ContentCategory.REGULATIONS_COMPLIANCE]: "Regulations & Compliance",
  [ContentCategory.TECHNICAL_SUPPORT]: "Technical Support & Troubleshooting",
  [ContentCategory.GENERAL]: "General",
};

/**
 * Get the display label for a content category
 */
export const getCategoryLabel = (category: ContentCategory): string => {
  return CONTENT_CATEGORY_LABELS[category] || "General";
};

/**
 * Get all available categories
 */
export const getAllCategories = (): ContentCategory[] => {
  return Object.values(ContentCategory);
};

/**
 * Get categories as options for dropdowns/selects
 */
export const getCategoryOptions = () => {
  return getAllCategories().map((category) => ({
    value: category,
    label: getCategoryLabel(category),
  }));
};
