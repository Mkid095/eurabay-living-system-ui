'use client';

import { useState, useEffect, useCallback } from 'react';
import { AdminGuard } from '@/components/auth/RoleGuard';
import { Spinner } from '@/components/ui/spinner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  getAllUsers,
  createUser,
  updateUserAdmin,
  deleteUser,
  setUserBannedStatus,
} from '@/lib/actions/user';
import { ROLE_DISPLAY_NAMES, type UserRole } from '@/lib/auth/rbac';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  SearchIcon,
  ShieldCheckIcon,
  ShieldAlertIcon,
  BanIcon,
  CheckIcon,
} from 'lucide-react';

type User = {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'trader' | 'viewer';
  emailVerified: boolean;
  image: string | null;
  createdAt: Date;
  updatedAt: Date;
  lastLogin?: Date;
};

type CreateUserData = {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
  role: 'admin' | 'trader' | 'viewer';
};

type EditUserData = {
  name: string;
  email: string;
  role: 'admin' | 'trader' | 'viewer';
};

const formatDate = (date: Date | string | undefined): string => {
  if (!date) return 'Never';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getRoleBadgeColor = (role: UserRole): string => {
  switch (role) {
    case 'admin':
      return 'bg-destructive/10 text-destructive border-destructive/20';
    case 'trader':
      return 'bg-primary/10 text-primary border-primary/20';
    case 'viewer':
      return 'bg-muted text-muted-foreground border-muted';
    default:
      return 'bg-muted text-muted-foreground border-muted';
  }
};

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [total, setTotal] = useState(0);

  // Create user dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createData, setCreateData] = useState<CreateUserData>({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    role: 'viewer',
  });
  const [createError, setCreateError] = useState('');
  const [createLoading, setCreateLoading] = useState(false);

  // Edit user dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editData, setEditData] = useState<EditUserData>({
    name: '',
    email: '',
    role: 'viewer',
  });
  const [editError, setEditError] = useState('');
  const [editLoading, setEditLoading] = useState(false);

  // Delete confirmation dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingUser, setDeletingUser] = useState<User | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Fetch users
  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getAllUsers({
        search: search || undefined,
        role: roleFilter !== 'all' ? (roleFilter as UserRole) : undefined,
      });

      if (result.success && result.data) {
        setUsers(result.data.users);
        setTotal(result.data.total);
      } else {
        console.error('Failed to fetch users:', result.error);
      }
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  }, [search, roleFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Create user handler
  const handleCreateUser = async () => {
    setCreateError('');

    // Validation
    if (!createData.name || createData.name.trim().length < 2) {
      setCreateError('Name must be at least 2 characters long.');
      return;
    }

    if (!createData.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(createData.email)) {
      setCreateError('Please enter a valid email address.');
      return;
    }

    if (!createData.password || createData.password.length < 8) {
      setCreateError('Password must be at least 8 characters long.');
      return;
    }

    if (createData.password !== createData.confirmPassword) {
      setCreateError('Passwords do not match.');
      return;
    }

    setCreateLoading(true);
    try {
      const result = await createUser({
        name: createData.name,
        email: createData.email,
        password: createData.password,
        role: createData.role,
      });

      if (result.success) {
        setCreateDialogOpen(false);
        setCreateData({
          name: '',
          email: '',
          password: '',
          confirmPassword: '',
          role: 'viewer',
        });
        await fetchUsers();
      } else {
        setCreateError(result.error || 'Failed to create user.');
      }
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : 'Failed to create user.');
    } finally {
      setCreateLoading(false);
    }
  };

  // Open edit dialog
  const openEditDialog = (user: User) => {
    setEditingUser(user);
    setEditData({
      name: user.name,
      email: user.email,
      role: user.role,
    });
    setEditError('');
    setEditDialogOpen(true);
  };

  // Edit user handler
  const handleEditUser = async () => {
    if (!editingUser) return;

    setEditError('');

    if (!editData.name || editData.name.trim().length < 2) {
      setEditError('Name must be at least 2 characters long.');
      return;
    }

    if (!editData.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(editData.email)) {
      setEditError('Please enter a valid email address.');
      return;
    }

    setEditLoading(true);
    try {
      const result = await updateUserAdmin(editingUser.id, {
        name: editData.name,
        email: editData.email,
        role: editData.role,
      });

      if (result.success) {
        setEditDialogOpen(false);
        setEditingUser(null);
        await fetchUsers();
      } else {
        setEditError(result.error || 'Failed to update user.');
      }
    } catch (error) {
      setEditError(error instanceof Error ? error.message : 'Failed to update user.');
    } finally {
      setEditLoading(false);
    }
  };

  // Open delete confirmation dialog
  const openDeleteDialog = (user: User) => {
    setDeletingUser(user);
    setDeleteDialogOpen(true);
  };

  // Delete user handler
  const handleDeleteUser = async () => {
    if (!deletingUser) return;

    setDeleteLoading(true);
    try {
      const result = await deleteUser(deletingUser.id);

      if (result.success) {
        setDeleteDialogOpen(false);
        setDeletingUser(null);
        await fetchUsers();
      } else {
        console.error('Failed to delete user:', result.error);
      }
    } catch (error) {
      console.error('Error deleting user:', error);
    } finally {
      setDeleteLoading(false);
    }
  };

  // Toggle ban status
  const toggleBanStatus = async (user: User) => {
    try {
      const result = await setUserBannedStatus(user.id, !user.emailVerified);
      if (result.success) {
        await fetchUsers();
      } else {
        console.error('Failed to update user status:', result.error);
      }
    } catch (error) {
      console.error('Error updating user status:', error);
    }
  };

  // Quick role change
  const handleRoleChange = async (userId: string, newRole: UserRole) => {
    try {
      const result = await updateUserAdmin(userId, { role: newRole });
      if (result.success) {
        await fetchUsers();
      } else {
        console.error('Failed to update role:', result.error);
      }
    } catch (error) {
      console.error('Error updating role:', error);
    }
  };

  return (
    <AdminGuard>
      <div className="container mx-auto py-8 px-4 max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <ShieldCheckIcon className="w-8 h-8 text-primary" />
            <h1 className="text-3xl font-bold">User Management</h1>
          </div>
          <p className="text-muted-foreground">
            Manage user accounts, roles, and access permissions
          </p>
        </div>

        {/* Actions Bar */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          {/* Search */}
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search by name or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* Role Filter */}
          <Select value={roleFilter} onValueChange={setRoleFilter}>
            <SelectTrigger className="w-full sm:w-[180px]">
              <SelectValue placeholder="Filter by role" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Roles</SelectItem>
              <SelectItem value="admin">Admin</SelectItem>
              <SelectItem value="trader">Trader</SelectItem>
              <SelectItem value="viewer">Viewer</SelectItem>
            </SelectContent>
          </Select>

          {/* Create User Button */}
          <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <PlusIcon className="w-4 h-4" />
                Create User
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Create New User</DialogTitle>
                <DialogDescription>
                  Add a new user to the system. They will receive their login credentials.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="create-name">Name</Label>
                  <Input
                    id="create-name"
                    placeholder="John Doe"
                    value={createData.name}
                    onChange={(e) => setCreateData({ ...createData, name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-email">Email</Label>
                  <Input
                    id="create-email"
                    type="email"
                    placeholder="john@example.com"
                    value={createData.email}
                    onChange={(e) => setCreateData({ ...createData, email: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-password">Password</Label>
                  <Input
                    id="create-password"
                    type="password"
                    placeholder="Min 8 characters"
                    value={createData.password}
                    onChange={(e) => setCreateData({ ...createData, password: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-confirm-password">Confirm Password</Label>
                  <Input
                    id="create-confirm-password"
                    type="password"
                    placeholder="Confirm password"
                    value={createData.confirmPassword}
                    onChange={(e) => setCreateData({ ...createData, confirmPassword: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-role">Role</Label>
                  <Select
                    value={createData.role}
                    onValueChange={(value) =>
                      setCreateData({ ...createData, role: value as UserRole })
                    }
                  >
                    <SelectTrigger id="create-role">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="viewer">Viewer - Read only</SelectItem>
                      <SelectItem value="trader">Trader - Can approve trades</SelectItem>
                      <SelectItem value="admin">Admin - Full access</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {createError && (
                  <p className="text-sm text-destructive">{createError}</p>
                )}
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setCreateDialogOpen(false)}
                  disabled={createLoading}
                >
                  Cancel
                </Button>
                <Button onClick={handleCreateUser} disabled={createLoading}>
                  {createLoading ? (
                    <>
                      <Spinner className="mr-2" />
                      Creating...
                    </>
                  ) : (
                    'Create User'
                  )}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {/* Users Table */}
        <div className="border rounded-lg overflow-hidden bg-background">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden md:table-cell">Created</TableHead>
                <TableHead className="hidden lg:table-cell">Last Login</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <Spinner />
                      <span className="text-muted-foreground">Loading users...</span>
                    </div>
                  </TableCell>
                </TableRow>
              ) : users.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                    No users found. Create a new user to get started.
                  </TableCell>
                </TableRow>
              ) : (
                users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center text-sm font-medium">
                          {user.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="font-medium">{user.name}</div>
                          <div className="text-sm text-muted-foreground">{user.email}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Select
                        value={user.role}
                        onValueChange={(value) => handleRoleChange(user.id, value as UserRole)}
                      >
                        <SelectTrigger className={`w-auto ${getRoleBadgeColor(user.role)} border`}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="viewer">Viewer</SelectItem>
                          <SelectItem value="trader">Trader</SelectItem>
                          <SelectItem value="admin">Admin</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell>
                      {user.emailVerified ? (
                        <div className="flex items-center gap-1.5 text-sm">
                          <CheckIcon className="w-4 h-4 text-primary" />
                          <span>Active</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-sm">
                          <BanIcon className="w-4 h-4 text-destructive" />
                          <span>Banned</span>
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="hidden md:table-cell text-sm text-muted-foreground">
                      {formatDate(user.createdAt)}
                    </TableCell>
                    <TableCell className="hidden lg:table-cell text-sm text-muted-foreground">
                      {formatDate(user.lastLogin)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => toggleBanStatus(user)}
                          title={user.emailVerified ? 'Ban user' : 'Unban user'}
                        >
                          {user.emailVerified ? (
                            <BanIcon className="w-4 h-4 text-destructive" />
                          ) : (
                            <CheckIcon className="w-4 h-4 text-primary" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => openEditDialog(user)}
                          title="Edit user"
                        >
                          <PencilIcon className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => openDeleteDialog(user)}
                          title="Delete user"
                        >
                          <TrashIcon className="w-4 h-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination info */}
        <div className="mt-4 text-sm text-muted-foreground">
          Showing {users.length} of {total} users
        </div>

        {/* Edit User Dialog */}
        <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Edit User</DialogTitle>
              <DialogDescription>
                Update user information and permissions.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="edit-name">Name</Label>
                <Input
                  id="edit-name"
                  value={editData.name}
                  onChange={(e) => setEditData({ ...editData, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-email">Email</Label>
                <Input
                  id="edit-email"
                  type="email"
                  value={editData.email}
                  onChange={(e) => setEditData({ ...editData, email: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-role">Role</Label>
                <Select
                  value={editData.role}
                  onValueChange={(value) => setEditData({ ...editData, role: value as UserRole })}
                >
                  <SelectTrigger id="edit-role">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="viewer">Viewer - Read only</SelectItem>
                    <SelectItem value="trader">Trader - Can approve trades</SelectItem>
                    <SelectItem value="admin">Admin - Full access</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {editError && <p className="text-sm text-destructive">{editError}</p>}
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setEditDialogOpen(false)}
                disabled={editLoading}
              >
                Cancel
              </Button>
              <Button onClick={handleEditUser} disabled={editLoading}>
                {editLoading ? (
                  <>
                    <Spinner className="mr-2" />
                    Saving...
                  </>
                ) : (
                  'Save Changes'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <ShieldAlertIcon className="w-5 h-5 text-destructive" />
                Delete User
              </DialogTitle>
              <DialogDescription>
                Are you sure you want to delete <strong>{deletingUser?.name}</strong>? This action
                cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}
                disabled={deleteLoading}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteUser}
                disabled={deleteLoading}
              >
                {deleteLoading ? (
                  <>
                    <Spinner className="mr-2" />
                    Deleting...
                  </>
                ) : (
                  'Delete User'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AdminGuard>
  );
}
