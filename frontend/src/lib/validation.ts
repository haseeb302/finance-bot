import { z } from "zod";

// Auth Validation Schemas
export const loginSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

export const registerSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
  username: z
    .string()
    .min(3, "Username must be at least 3 characters")
    .max(100, "Username must be less than 100 characters")
    .regex(
      /^[a-zA-Z0-9_]+$/,
      "Username can only contain letters, numbers, and underscores"
    ),
  full_name: z
    .string()
    .max(255, "Full name must be less than 255 characters")
    .optional(),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .max(100, "Password must be less than 100 characters")
    .regex(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      "Password must contain at least one uppercase letter, one lowercase letter, and one number"
    ),
});

export const forgotPasswordSchema = z.object({
  email: z.string().email("Please enter a valid email address"),
});

export const resetPasswordSchema = z.object({
  token: z.string().min(1, "Reset token is required"),
  new_password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .max(100, "Password must be less than 100 characters")
    .regex(
      /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      "Password must contain at least one uppercase letter, one lowercase letter, and one number"
    ),
});

// Chat Validation Schemas
export const messageSchema = z.object({
  message: z
    .string()
    .min(1, "Message cannot be empty")
    .max(10000, "Message must be less than 10,000 characters"),
  chat_id: z.number().optional(),
  session_id: z.string().optional(),
});

export const chatTitleSchema = z.object({
  title: z
    .string()
    .min(1, "Chat title cannot be empty")
    .max(255, "Chat title must be less than 255 characters"),
});

// Pagination Validation
export const paginationSchema = z.object({
  page: z.number().min(1).default(1),
  page_size: z.number().min(1).max(100).default(3),
});

// Type exports
export type LoginFormData = z.infer<typeof loginSchema>;
export type RegisterFormData = z.infer<typeof registerSchema>;
export type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;
export type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;
export type MessageFormData = z.infer<typeof messageSchema>;
export type ChatTitleFormData = z.infer<typeof chatTitleSchema>;
export type PaginationParams = z.infer<typeof paginationSchema>;
