'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';
import { Progress } from '@/components/ui/progress';

type PasswordStrength = 'weak' | 'medium' | 'strong';

export default function RegisterPage() {
  const router = useRouter();
  const { register, loading, isAuthenticated } = useAuth();

  const [name, setName] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [agreeToTerms, setAgreeToTerms] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [passwordStrength, setPasswordStrength] = useState<PasswordStrength>('weak');
  const [passwordScore, setPasswordScore] = useState<number>(0);

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [loading, isAuthenticated, router]);

  // Calculate password strength
  useEffect(() => {
    if (!password) {
      setPasswordScore(0);
      setPasswordStrength('weak');
      return;
    }

    let score = 0;

    // Length check
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;

    // Complexity checks
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
    if (/\d/.test(password)) score += 1;
    if (/[^a-zA-Z0-9]/.test(password)) score += 1;

    setPasswordScore(score);

    // Determine strength label
    if (score <= 2) {
      setPasswordStrength('weak');
    } else if (score <= 3) {
      setPasswordStrength('medium');
    } else {
      setPasswordStrength('strong');
    }
  }, [password]);

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validatePassword = (password: string): boolean => {
    return password.length >= 8;
  };

  const getPasswordStrengthColor = (): string => {
    switch (passwordStrength) {
      case 'weak':
        return 'bg-destructive';
      case 'medium':
        return 'bg-yellow-500';
      case 'strong':
        return 'bg-green-500';
      default:
        return 'bg-destructive';
    }
  };

  const getPasswordStrengthText = (): string => {
    if (!password) return '';
    return passwordStrength.charAt(0).toUpperCase() + passwordStrength.slice(1);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate name
    if (!name.trim()) {
      setError('Please enter your name');
      return;
    }

    // Validate email format
    if (!validateEmail(email)) {
      setError('Please enter a valid email address');
      return;
    }

    // Validate password minimum length
    if (!validatePassword(password)) {
      setError('Password must be at least 8 characters');
      return;
    }

    // Validate password matching
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    // Validate terms agreement
    if (!agreeToTerms) {
      setError('You must agree to the Terms of Service');
      return;
    }

    setIsSubmitting(true);

    try {
      const result = await register({ name, email, password });

      if (result.success) {
        // Redirect to dashboard on successful registration
        router.push('/dashboard');
      } else {
        // Show error message for failed registration
        setError(result.error || 'Registration failed. Please try again.');
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Show loading state while checking authentication
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <Spinner className="mx-auto size-8" />
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Create Account</CardTitle>
          <CardDescription>
            Sign up to get started with your account
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {/* Error message */}
            {error && (
              <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            {/* Name field */}
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                type="text"
                placeholder="Enter your full name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isSubmitting}
                required
                autoComplete="name"
              />
            </div>

            {/* Email field */}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="your.email@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isSubmitting}
                required
                autoComplete="email"
              />
            </div>

            {/* Password field */}
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Create a password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isSubmitting}
                required
                autoComplete="new-password"
                minLength={8}
              />
              {/* Password strength indicator */}
              {password && (
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Password strength:</span>
                    <span className={`font-medium ${
                      passwordStrength === 'weak' ? 'text-destructive' :
                      passwordStrength === 'medium' ? 'text-yellow-500' :
                      'text-green-500'
                    }`}>
                      {getPasswordStrengthText()}
                    </span>
                  </div>
                  <Progress value={(passwordScore / 5) * 100} className="h-1">
                    <div className={`h-full ${getPasswordStrengthColor()} transition-all`} />
                  </Progress>
                </div>
              )}
            </div>

            {/* Confirm password field */}
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="Confirm your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isSubmitting}
                required
                autoComplete="new-password"
                minLength={8}
              />
              {confirmPassword && password !== confirmPassword && (
                <p className="text-xs text-destructive">Passwords do not match</p>
              )}
            </div>

            {/* Terms of service checkbox */}
            <div className="flex items-start space-x-2">
              <Checkbox
                id="terms"
                checked={agreeToTerms}
                onCheckedChange={(checked) => setAgreeToTerms(checked === true)}
                disabled={isSubmitting}
              />
              <Label
                htmlFor="terms"
                className="cursor-pointer font-normal text-muted-foreground text-sm leading-tight"
              >
                I agree to the{' '}
                <Link href="/terms" className="text-primary hover:underline">
                  Terms of Service
                </Link>
                {' '}and{' '}
                <Link href="/privacy" className="text-primary hover:underline">
                  Privacy Policy
                </Link>
              </Label>
            </div>
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            {/* Submit button with loading spinner */}
            <Button
              type="submit"
              className="w-full"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Spinner className="mr-2" />
                  Creating account...
                </>
              ) : (
                'Create Account'
              )}
            </Button>

            {/* Sign in link */}
            <div className="text-center text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link href="/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
