'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { updateUserProfile, changePassword, getUserProfile } from '@/lib/actions/user';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Spinner } from '@/components/ui/spinner';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';

interface ProfileData {
  user: {
    id: string;
    email: string;
    name: string;
    role: 'admin' | 'trader' | 'viewer';
    emailVerified: boolean;
    image: string | null;
    createdAt: Date;
    updatedAt: Date;
  };
  createdAt: Date;
  lastLogin?: Date;
}

export default function ProfilePage() {
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated, refreshSession } = useAuth();

  const [profileData, setProfileData] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Edit profile form state
  const [editName, setEditName] = useState('');
  const [editImage, setEditImage] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);

  // Change password form state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login?redirect=/profile');
    }
  }, [authLoading, isAuthenticated, router]);

  // Fetch profile data
  useEffect(() => {
    async function fetchProfile() {
      if (user) {
        try {
          const response = await getUserProfile();
          if (response.success && response.data) {
            setProfileData(response.data);
            setEditName(response.data.user.name || '');
            setEditImage(response.data.user.image || '');
          } else {
            setErrorMessage(response.error || 'Failed to load profile');
          }
        } catch (err) {
          setErrorMessage('Failed to load profile');
        } finally {
          setLoading(false);
        }
      }
    }

    if (user && isAuthenticated) {
      fetchProfile();
    }
  }, [user, isAuthenticated]);

  const handleSaveProfile = async () => {
    setErrorMessage('');
    setSuccessMessage('');

    // Validate name
    if (!editName.trim()) {
      setErrorMessage('Name is required');
      return;
    }

    if (editName.trim().length < 2) {
      setErrorMessage('Name must be at least 2 characters');
      return;
    }

    setSavingProfile(true);

    try {
      const result = await updateUserProfile({
        name: editName.trim(),
        image: editImage.trim() || null,
      });

      if (result.success) {
        setSuccessMessage('Profile updated successfully');
        // Refresh session to get updated user data
        await refreshSession();
        // Reload profile data
        const profileResponse = await getUserProfile();
        if (profileResponse.success && profileResponse.data) {
          setProfileData(profileResponse.data);
        }
      } else {
        setErrorMessage(result.error || 'Failed to update profile');
      }
    } catch (err) {
      setErrorMessage('An unexpected error occurred');
    } finally {
      setSavingProfile(false);
    }
  };

  const handleChangePassword = async () => {
    setErrorMessage('');
    setSuccessMessage('');

    // Validate current password
    if (!currentPassword) {
      setErrorMessage('Current password is required');
      return;
    }

    // Validate new password
    if (!newPassword || newPassword.length < 8) {
      setErrorMessage('New password must be at least 8 characters');
      return;
    }

    // Validate password confirmation
    if (newPassword !== confirmPassword) {
      setErrorMessage('New passwords do not match');
      return;
    }

    // Check that new password is different from current
    if (currentPassword === newPassword) {
      setErrorMessage('New password must be different from current password');
      return;
    }

    setChangingPassword(true);

    try {
      const result = await changePassword({
        currentPassword,
        newPassword,
        revokeOtherSessions: true,
      });

      if (result.success) {
        setSuccessMessage('Password changed successfully');
        // Clear form
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } else {
        setErrorMessage(result.error || 'Failed to change password');
      }
    } catch (err) {
      setErrorMessage('An unexpected error occurred');
    } finally {
      setChangingPassword(false);
    }
  };

  const formatDate = (date: Date | string | undefined): string => {
    if (!date) return 'Unknown';
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getInitials = (name: string): string => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  // Show loading while checking auth
  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <Spinner className="mx-auto size-8" />
          <p className="mt-4 text-muted-foreground">Loading profile...</p>
        </div>
      </div>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!isAuthenticated || !user || !profileData) {
    return null;
  }

  const roleColors: Record<string, string> = {
    admin: 'bg-red-500/10 text-red-500 dark:bg-red-500/20',
    trader: 'bg-blue-500/10 text-blue-500 dark:bg-blue-500/20',
    viewer: 'bg-gray-500/10 text-gray-500 dark:bg-gray-500/20',
  };

  return (
    <div className="container mx-auto max-w-4xl py-8 px-4">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">My Profile</h1>
        <p className="text-muted-foreground">Manage your account settings and preferences</p>
      </div>

      {/* Success/Error messages */}
      {successMessage && (
        <div className="mb-6 rounded-md bg-green-500/15 p-4 text-sm text-green-500 dark:bg-green-500/10">
          {successMessage}
        </div>
      )}
      {errorMessage && (
        <div className="mb-6 rounded-md bg-destructive/15 p-4 text-sm text-destructive">
          {errorMessage}
        </div>
      )}

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="edit">Edit Profile</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>Your account details and information</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Avatar and basic info */}
              <div className="flex items-center gap-6">
                <Avatar className="size-20">
                  <AvatarFallback className="text-lg font-semibold">
                    {getInitials(profileData.user.name)}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <h2 className="text-2xl font-semibold">{profileData.user.name}</h2>
                  <p className="text-muted-foreground">{profileData.user.email}</p>
                  <div className="mt-2">
                    <Badge className={roleColors[profileData.user.role] || ''}>
                      {profileData.user.role.toUpperCase()}
                    </Badge>
                  </div>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label className="text-muted-foreground">Email</Label>
                  <p className="font-medium">{profileData.user.email}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Name</Label>
                  <p className="font-medium">{profileData.user.name}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Role</Label>
                  <p className="font-medium capitalize">{profileData.user.role}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Email Verified</Label>
                  <p className="font-medium">
                    {profileData.user.emailVerified ? 'Yes' : 'No'}
                  </p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Account Created</Label>
                  <p className="font-medium">{formatDate(profileData.createdAt)}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">Last Login</Label>
                  <p className="font-medium">{formatDate(profileData.lastLogin)}</p>
                </div>
              </div>

              <div>
                <Label className="text-muted-foreground">Profile Picture</Label>
                {profileData.user.image ? (
                  <div className="mt-2">
                    <img
                      src={profileData.user.image}
                      alt="Profile"
                      className="size-32 rounded-full border-2 border-border"
                    />
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No profile picture set</p>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Edit Profile Tab */}
        <TabsContent value="edit">
          <Card>
            <CardHeader>
              <CardTitle>Edit Profile</CardTitle>
              <CardDescription>Update your profile information</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="edit-name">Name</Label>
                <Input
                  id="edit-name"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="Your full name"
                  disabled={savingProfile}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-image">Profile Picture URL (optional)</Label>
                <Input
                  id="edit-image"
                  value={editImage}
                  onChange={(e) => setEditImage(e.target.value)}
                  placeholder="https://example.com/avatar.jpg"
                  disabled={savingProfile}
                />
                <p className="text-xs text-muted-foreground">
                  Enter a URL for your profile picture
                </p>
              </div>

              <Button
                onClick={handleSaveProfile}
                disabled={savingProfile}
                className="w-full md:w-auto"
              >
                {savingProfile ? (
                  <>
                    <Spinner className="mr-2 size-4" />
                    Saving...
                  </>
                ) : (
                  'Save Changes'
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>Change Password</CardTitle>
              <CardDescription>Update your password to keep your account secure</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="current-password">Current Password</Label>
                <Input
                  id="current-password"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter your current password"
                  disabled={changingPassword}
                  autoComplete="current-password"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="new-password">New Password</Label>
                <Input
                  id="new-password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter your new password"
                  disabled={changingPassword}
                  autoComplete="new-password"
                  minLength={8}
                />
                <p className="text-xs text-muted-foreground">
                  Password must be at least 8 characters
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm-password">Confirm New Password</Label>
                <Input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm your new password"
                  disabled={changingPassword}
                  autoComplete="new-password"
                  minLength={8}
                />
              </div>

              <Button
                onClick={handleChangePassword}
                disabled={changingPassword}
                variant="destructive"
                className="w-full md:w-auto"
              >
                {changingPassword ? (
                  <>
                    <Spinner className="mr-2 size-4" />
                    Changing Password...
                  </>
                ) : (
                  'Change Password'
                )}
              </Button>

              <p className="text-xs text-muted-foreground">
                After changing your password, you will be logged out from all other devices
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
