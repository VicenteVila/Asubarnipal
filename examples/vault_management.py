"""Vault management example."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vault_manager import VaultManager


def main():
    """Run vault management demonstration."""
    print("=" * 60)
    print("Asubarnipal - Vault Management Demo")
    print("=" * 60)

    vm = VaultManager()

    # List existing vaults
    print("\n[1] Listing vaults...")
    vaults = vm.list_vaults()
    if vaults:
        for v in vaults:
            print(f"  - {v}")
    else:
        print("  No vaults found.")

    # Show active vault
    print(f"\n[2] Active vault: {vm.active_vault}")

    # Show vault info
    print("\n[3] Vault info:")
    try:
        info = vm.get_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"  [Error] {e}")

    # Create a demo vault (if not exists)
    demo_vault = "demo_vault"
    print(f"\n[4] Creating demo vault '{demo_vault}'...")
    try:
        vm.create(demo_vault)
        print(f"  Created: {demo_vault}")
    except Exception as e:
        print(f"  [Note] {e}")

    # Switch to demo vault
    print(f"\n[5] Switching to '{demo_vault}'...")
    try:
        vm.switch(demo_vault)
        print(f"  Active vault is now: {vm.active_vault}")
    except Exception as e:
        print(f"  [Error] {e}")

    # Switch back to principal
    print("\n[6] Switching back to 'principal'...")
    try:
        vm.switch("principal")
        print(f"  Active vault is now: {vm.active_vault}")
    except Exception as e:
        print(f"  [Note] {e}")

    print("\n" + "=" * 60)
    print("Demo complete!")


if __name__ == "__main__":
    main()
