import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/rbac/permission_catalog.dart';
import '../../../core/theme/app_spacing.dart';
import '../data/access_role_repository.dart';

class AccessRolesScreen extends ConsumerStatefulWidget {
  const AccessRolesScreen({super.key});

  @override
  ConsumerState<AccessRolesScreen> createState() => _AccessRolesScreenState();
}

class _AccessRolesScreenState extends ConsumerState<AccessRolesScreen> {
  List<AccessRoleSummary> _roles = const [];
  var _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final roles = await ref.read(accessRoleRepositoryProvider).listRoles(includeInactive: true);
      if (mounted) setState(() => _roles = roles);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openEditor({AccessRoleSummary? role}) async {
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _AccessRoleEditorSheet(roleId: role?.id),
    );
    if (saved == true) await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openEditor(),
        icon: const Icon(Icons.add),
        label: const Text('New role'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(AppSpacing.md),
                children: [
                  Text(
                    'Create named roles and choose exactly which sections users can view, edit, or export.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: AppSpacing.md),
                  if (_error != null)
                    Card(
                      color: Theme.of(context).colorScheme.errorContainer,
                      child: ListTile(title: Text(_error!)),
                    ),
                  if (_roles.isEmpty && _error == null)
                    const Padding(
                      padding: EdgeInsets.all(AppSpacing.xl),
                      child: Center(child: Text('No custom roles yet.')),
                    ),
                  for (final role in _roles)
                    Card(
                      child: ListTile(
                        title: Text(role.name),
                        subtitle: Text(
                          '${role.permissionCount} permissions · ${role.assignedUserCount} users'
                          '${role.isActive ? '' : ' · Inactive'}',
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => _openEditor(role: role),
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}

class _AccessRoleEditorSheet extends ConsumerStatefulWidget {
  const _AccessRoleEditorSheet({this.roleId});

  final int? roleId;

  @override
  ConsumerState<_AccessRoleEditorSheet> createState() => _AccessRoleEditorSheetState();
}

class _AccessRoleEditorSheetState extends ConsumerState<_AccessRoleEditorSheet> {
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _selected = <String>{};
  var _loading = true;
  var _saving = false;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    if (widget.roleId == null) {
      setState(() => _loading = false);
      return;
    }
    try {
      final role = await ref.read(accessRoleRepositoryProvider).getRole(widget.roleId!);
      _nameController.text = role.name;
      _descriptionController.text = role.description ?? '';
      _selected.addAll(role.permissions);
    } catch (_) {
      // Keep empty editor.
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  void _toggleAll(bool select) {
    setState(() {
      _selected
        ..clear()
        ..addAll(select ? allAssignablePermissionIds : const []);
    });
  }

  Future<void> _save() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) return;
    setState(() => _saving = true);
    try {
      final repo = ref.read(accessRoleRepositoryProvider);
      final permissions = _selected.toList()..sort();
      if (widget.roleId == null) {
        await repo.createRole(
          name: name,
          description: _descriptionController.text.trim(),
          permissions: permissions,
        );
      } else {
        await repo.updateRole(
          widget.roleId!,
          name: name,
          description: _descriptionController.text.trim(),
          permissions: permissions,
        );
      }
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final allSelected = allAssignablePermissionIds.every(_selected.contains);
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.88,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            widget.roleId == null ? 'New access role' : 'Edit access role',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                        ),
                        TextButton(
                          onPressed: () => _toggleAll(!allSelected),
                          child: Text(allSelected ? 'Clear all' : 'Select all'),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: ListView(
                      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
                      children: [
                        TextField(
                          controller: _nameController,
                          decoration: const InputDecoration(labelText: 'Role name'),
                        ),
                        TextField(
                          controller: _descriptionController,
                          decoration: const InputDecoration(labelText: 'Description'),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        for (final group in kAssignablePermissionGroups) ...[
                          Text(group.label, style: Theme.of(context).textTheme.titleSmall),
                          const SizedBox(height: AppSpacing.sm),
                          for (final option in group.permissions)
                            CheckboxListTile(
                              value: _selected.contains(option.id),
                              onChanged: (checked) {
                                setState(() {
                                  if (checked == true) {
                                    _selected.add(option.id);
                                  } else {
                                    _selected.remove(option.id);
                                  }
                                });
                              },
                              title: Text(option.label),
                              subtitle: Text(option.description),
                              controlAffinity: ListTileControlAffinity.leading,
                              contentPadding: EdgeInsets.zero,
                            ),
                          const Divider(height: 24),
                        ],
                      ],
                    ),
                  ),
                  SafeArea(
                    child: Padding(
                      padding: const EdgeInsets.all(AppSpacing.md),
                      child: FilledButton(
                        onPressed: _saving ? null : _save,
                        child: Text(_saving ? 'Saving…' : 'Save role'),
                      ),
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
