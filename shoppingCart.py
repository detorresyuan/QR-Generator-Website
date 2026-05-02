class ShoppingCartItem:
    """Represents an item in the shopping cart (a node in the doubly linked list)."""
    def __init__(self, item_name, price):
        self.item_name = item_name
        self.price = price
        self.prev = None  # Pointer to the previous node
        self.next = None  # Pointer to the next node

    def __str__(self):
        return f"{self.item_name} (${self.price:.2f})"

class DoublyLinkedListShoppingCart:
    """Represents the shopping cart using a Doubly Linked List."""
    def __init__(self):
        self.head = None
        self.tail = None
        self.count = 0

    # === Insertion (Adding a new item to the cart) ===
    def add_item(self, item_name, price):
        """Adds a new item to the end of the cart (list)."""
        new_item = ShoppingCartItem(item_name, price)

        if not self.head:
            # Cart is empty
            self.head = new_item
            self.tail = new_item
        else:
            # Cart is not empty, add to the end
            new_item.prev = self.tail
            self.tail.next = new_item
            self.tail = new_item

        self.count += 1
        print(f"✅ Added: {new_item.item_name} to the cart.")
        # This is where **Insertion** occurs.

    # === Deletion (Removing an item from the cart) ===
    def remove_item(self, item_name):
        """Removes the first occurrence of an item with the given name."""
        current = self.head
        found = False

        while current:
            if current.item_name == item_name:
                # Found the item to delete
                found = True

                if current == self.head and current == self.tail:
                    # Case 1: Only one item in the list
                    self.head = None
                    self.tail = None
                elif current == self.head:
                    # Case 2: Deleting the head
                    self.head = current.next
                    if self.head:
                        self.head.prev = None
                elif current == self.tail:
                    # Case 3: Deleting the tail
                    self.tail = current.prev
                    if self.tail:
                        self.tail.next = None
                else:
                    # Case 4: Deleting a node in the middle
                    current.prev.next = current.next
                    current.next.prev = current.prev

                self.count -= 1
                print(f"🗑️ Removed: {item_name} from the cart.")
                # This is where **Deletion** occurs.
                return

            current = current.next

        if not found:
            print(f"❌ Item not found: {item_name} is not in the cart.")


    # === Traversal (Viewing all items in the cart) ===
    def display_cart(self):
        """Displays all items in the cart (forward traversal)."""
        if not self.head:
            print("🛒 Your cart is empty.")
            return

        print("\n--- Current Shopping Cart Items ---")
        current = self.head
        total_price = 0

        while current:
            print(f"- {current}")
            total_price += current.price
            current = current.next # Moving to the next node
            # This is where **Traversal** occurs (moving forward).

        print(f"-----------------------------------")
        print(f"Total Items: {self.count} | Total Price: ${total_price:.2f}")

    def display_cart_reverse(self):
        """Displays all items in reverse order (backward traversal)."""
        if not self.tail:
            print("🛒 Your cart is empty.")
            return

        print("\n--- Shopping Cart (Reverse Order) ---")
        current = self.tail

        while current:
            print(f"- {current}")
            current = current.prev # Moving to the previous node
            # This is also **Traversal** (moving backward).

# --- Program Execution ---
cart = DoublyLinkedListShoppingCart()

cart.add_item("Laptop", 1200.00)  # Insertion 1
cart.add_item("Mouse", 25.50)     # Insertion 2
cart.add_item("Keyboard", 75.00)  # Insertion 3
cart.add_item("Monitor", 300.00)

cart.display_cart() # Traversal 1

cart.remove_item("Mouse") # Deletion 1
cart.remove_item("Webcam") # Item not found

cart.display_cart() # Traversal 2

cart.display_cart_reverse() # Traversal 3 (Backward)