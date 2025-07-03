#!/usr/bin/env python3
"""
Ixina Tools – Toestellenmanager (v2.0, refactored)

Een moderne, robuuste applicatie voor het beheren van keukentoestellen.
Volledig herschreven met focus op onderhoudbaarheid, prestaties en uitbreidbaarheid.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Callable, Any
from functools import lru_cache
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageDraw, ImageOps, ImageFont

BASE_DIR = Path(__file__).parent
LOGO_IMAGE_PATH = BASE_DIR / "logo.png"

# ============================================================================
# Configuration and Constants
# ============================================================================

@dataclass
class AppConfig:
    """Application configuration with sensible defaults."""
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent)
    img_dir: Path = field(init=False)
    img_size: tuple[int, int] = (160, 110)
    vat_rates: dict[str, float] = field(default_factory=lambda: {"high": 0.21, "low": 0.06})
    cache_size: int = 100

    def __post_init__(self):
        self.img_dir = self.base_dir / "images"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ElectricBlock:
    """Represents an electrical block configuration."""
    name: str
    min_points: int
    max_points: int


@dataclass
class Appliance:
    """Represents a kitchen appliance."""
    code: str
    brand: str
    category: str
    points: int
    price_ex: float
    option: Optional[str] = None
    img: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Appliance':
        """Create Appliance from dictionary with validation."""
        required_fields = {'code', 'brand', 'category', 'punten', 'price_ex'}
        if not all(field in data for field in required_fields):
            raise ValueError(f"Missing required fields in appliance data: {data}")

        return cls(
            code=str(data['code']),
            brand=str(data['brand']),
            category=str(data['category']),
            points=int(data['punten']),
            price_ex=float(data['price_ex']),
            option=data.get('option'),
            img=data.get('img')
        )


@dataclass
class CartItem:
    """Represents an item in the shopping cart."""
    appliance: Appliance
    quantity: int = 1


# ============================================================================
# Business Logic Layer
# ============================================================================

class DataRepository(ABC):
    """Abstract repository for data access."""

    @abstractmethod
    def load_blocks(self) -> Dict[str, ElectricBlock]:
        pass

    @abstractmethod
    def load_appliances(self) -> List[Appliance]:
        pass


class JSONDataRepository(DataRepository):
    """File-based data repository using JSON."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def load_blocks(self) -> Dict[str, ElectricBlock]:
        """Load electrical blocks from JSON file."""
        try:
            blocks_file = self.config.base_dir / "blocks.json"
            with open(blocks_file, encoding="utf-8") as f:
                data = json.load(f)

            blocks = {}
            for name, (min_pts, max_pts) in data.items():
                blocks[name] = ElectricBlock(name, min_pts, max_pts)

            self.logger.info(f"Loaded {len(blocks)} electrical blocks")
            return blocks

        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Failed to load blocks: {e}")
            # Return default blocks as fallback
            return {"Default": ElectricBlock("Default", 0, 100)}

    def load_appliances(self) -> List[Appliance]:
        """Load appliances from JSON file."""
        try:
            appliances_file = self.config.base_dir / "appliances.json"
            with open(appliances_file, encoding="utf-8") as f:
                data = json.load(f)

            appliances = []
            for item in data:
                try:
                    appliances.append(Appliance.from_dict(item))
                except ValueError as e:
                    self.logger.warning(f"Skipping invalid appliance: {e}")

            self.logger.info(f"Loaded {len(appliances)} appliances")
            return appliances

        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load appliances: {e}")
            return []


class ImageCache:
    """Efficient image caching with memory management."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.cache: Dict[Optional[str], ctk.CTkImage] = {}
        self.logger = logging.getLogger(__name__)

    @lru_cache(maxsize=100)
    def load_image(self, filename: Optional[str] = None) -> ctk.CTkImage:
        """Load and cache image with fallback to placeholder."""
        if filename in self.cache:
            return self.cache[filename]

        try:
            if filename:
                img_path = self.config.img_dir / filename
                if img_path.is_file() and self._is_safe_path(img_path):
                    image = Image.open(img_path)
                    image = ImageOps.contain(image, self.config.img_size)
                else:
                    image = self._create_placeholder("Not Found")
            else:
                image = self._create_placeholder("No Image")

            ctk_image = ctk.CTkImage(image, size=self.config.img_size)
            self.cache[filename] = ctk_image
            return ctk_image

        except Exception as e:
            self.logger.warning(f"Failed to load image {filename}: {e}")
            return self._get_error_image()

    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is safe (prevent directory traversal)."""
        try:
            path.resolve().relative_to(self.config.img_dir.resolve())
            return True
        except ValueError:
            return False

    def _create_placeholder(self, text: str) -> Image.Image:
        """Create placeholder image with text."""
        image = Image.new("RGB", self.config.img_size, "#444444")
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (self.config.img_size[0] - text_width) // 2
        y = (self.config.img_size[1] - text_height) // 2
        draw.text((x, y), text, fill="white", font=font)

        return image

    def _get_error_image(self) -> ctk.CTkImage:
        """Return cached error image."""
        if "ERROR" not in self.cache:
            self.cache["ERROR"] = ctk.CTkImage(
                self._create_placeholder("Error"),
                size=self.config.img_size
            )
        return self.cache["ERROR"]


class ApplianceFilter:
    """Handles appliance filtering logic."""

    def __init__(self, appliances: List[Appliance]):
        self.appliances = appliances
        self._build_indexes()

    def _build_indexes(self):
        """Build indexes for efficient filtering."""
        self.by_category = {}
        self.by_brand = {}
        self.by_points = {}

        for appliance in self.appliances:
            # Category index
            if appliance.category not in self.by_category:
                self.by_category[appliance.category] = []
            self.by_category[appliance.category].append(appliance)

            # Brand index
            if appliance.brand not in self.by_brand:
                self.by_brand[appliance.brand] = []
            self.by_brand[appliance.brand].append(appliance)

            # Points index
            points_range = appliance.points // 10 * 10  # Group by tens
            if points_range not in self.by_points:
                self.by_points[points_range] = []
            self.by_points[points_range].append(appliance)

    def filter(self,
               category: Optional[str] = None,
               brand: Optional[str] = None,
               option: Optional[str] = None,
               max_points: Optional[int] = None,
               search_term: Optional[str] = None) -> List[Appliance]:
        """Filter appliances based on criteria."""
        result = self.appliances.copy()

        if category and category != "-":
            result = [a for a in result if a.category == category]

        if brand and brand != "-":
            result = [a for a in result if a.brand == brand]

        if option and option != "-":
            result = [a for a in result if (a.option or "-") == option]

        if max_points is not None:
            result = [a for a in result if a.points <= max_points]

        if search_term:
            search_lower = search_term.lower()
            result = [a for a in result if
                      search_lower in a.code.lower() or
                      search_lower in a.brand.lower()]

        return result

    def get_brands_for_category(self, category: str, max_points: Optional[int] = None) -> List[str]:
        """Get available brands for a category."""
        appliances = self.by_category.get(category, [])
        if max_points is not None:
            appliances = [a for a in appliances if a.points <= max_points]

        brands = sorted(set(a.brand for a in appliances))
        return brands or ["-"]


class ShoppingCart:
    """Manages shopping cart operations."""

    def __init__(self):
        self.items: List[CartItem] = []
        self.observers: List[Callable[[], None]] = []

    def add_item(self, appliance: Appliance) -> None:
        """Add appliance to cart."""
        # Check if item already exists
        for item in self.items:
            if item.appliance.code == appliance.code:
                item.quantity += 1
                break
        else:
            self.items.append(CartItem(appliance))

        self._notify_observers()

    def remove_item(self, appliance: Appliance) -> None:
        """Remove appliance from cart."""
        self.items = [item for item in self.items if item.appliance.code != appliance.code]
        self._notify_observers()

    def clear(self) -> None:
        """Clear all items from cart."""
        self.items.clear()
        self._notify_observers()

    def get_total_points(self) -> int:
        """Calculate total points in cart."""
        return sum(item.appliance.points * item.quantity for item in self.items)

    def get_total_price(self, vat_rate: float) -> float:
        """Calculate total price including VAT."""
        total_ex = sum(item.appliance.price_ex * item.quantity for item in self.items)
        return round(total_ex * (1 + vat_rate), 2)

    def add_observer(self, callback: Callable[[], None]) -> None:
        """Add cart change observer."""
        self.observers.append(callback)

    def _notify_observers(self) -> None:
        """Notify all observers of cart changes."""
        for callback in self.observers:
            try:
                callback()
            except Exception as e:
                logging.getLogger(__name__).error(f"Observer callback failed: {e}")


# ============================================================================
# UI Components
# ============================================================================

class FilterPanel(ctk.CTkFrame):
    """Left panel containing all filter controls."""

    def __init__(self, master, config: AppConfig, on_filter_change: Callable):
        super().__init__(master)
        self.config = config
        self.on_filter_change = on_filter_change

        # UI State
        self.block_var = ctk.StringVar()
        self.brand_var = ctk.StringVar()
        self.category_var = ctk.StringVar()
        self.suboption_var = ctk.StringVar()
        self.search_var = ctk.StringVar()
        self.vat_switch = None

        self._build_ui()
        self._setup_callbacks()

    def _build_ui(self):
        """Build the filter panel UI."""
        self.columnconfigure(0, weight=1)

        row = 0

        # Electric Block Selection
        ctk.CTkLabel(self, text="Elektrisch Blok", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, sticky="w", pady=(5, 2))
        row += 1

        self.block_menu = ctk.CTkOptionMenu(self, variable=self.block_var, values=[])
        self.block_menu.grid(row=row, column=0, sticky="ew", pady=2)
        row += 1

        # VAT Rate Switch
        ctk.CTkLabel(self, text="BTW Tarief", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, sticky="w", pady=(15, 2))
        row += 1

        vat_frame = ctk.CTkFrame(self)
        vat_frame.grid(row=row, column=0, sticky="ew", pady=2)
        vat_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(vat_frame, text="21%").grid(row=0, column=0, padx=5)
        self.vat_switch = ctk.CTkSwitch(vat_frame, text="")
        self.vat_switch.grid(row=0, column=1, padx=5)
        ctk.CTkLabel(vat_frame, text="6%").grid(row=0, column=2, padx=5)
        row += 1

        # Search
        ctk.CTkLabel(self, text="Zoeken", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, sticky="w", pady=(15, 2))
        row += 1

        self.search_entry = ctk.CTkEntry(self, textvariable=self.search_var,
                                         placeholder_text="Zoek op code of merk...")
        self.search_entry.grid(row=row, column=0, sticky="ew", pady=2)
        row += 1

        # Category Selection
        ctk.CTkLabel(self, text="Categorie", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, sticky="w", pady=(15, 2))
        row += 1

        self.category_menu = ctk.CTkOptionMenu(self, variable=self.category_var, values=[])
        self.category_menu.grid(row=row, column=0, sticky="ew", pady=2)
        row += 1

        # Brand Selection
        ctk.CTkLabel(self, text="Merk", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, sticky="w", pady=(15, 2))
        row += 1

        self.brand_menu = ctk.CTkOptionMenu(self, variable=self.brand_var, values=[])
        self.brand_menu.grid(row=row, column=0, sticky="ew", pady=2)
        row += 1

        # Suboption Selection
        ctk.CTkLabel(self, text="Optie", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, sticky="w", pady=(15, 2))
        row += 1

        self.suboption_menu = ctk.CTkOptionMenu(self, variable=self.suboption_var, values=[])
        self.suboption_menu.grid(row=row, column=0, sticky="ew", pady=2)

    def _setup_callbacks(self):
        """Setup callbacks for UI controls."""
        self.block_var.trace_add("write", lambda *_: self.on_filter_change())
        self.brand_var.trace_add("write", lambda *_: self.on_filter_change())
        self.category_var.trace_add("write", lambda *_: self._on_category_change())
        self.suboption_var.trace_add("write", lambda *_: self.on_filter_change())
        self.search_var.trace_add("write", lambda *_: self.on_filter_change())
        self.vat_switch.configure(command=self.on_filter_change)

    def _on_category_change(self):
        """Handle category change - update suboptions."""
        category = self.category_var.get()
        suboptions = self._get_suboptions_for_category(category)

        self.suboption_menu.configure(values=suboptions)
        if suboptions:
            self.suboption_var.set(suboptions[0])

        self.on_filter_change()

    def _get_suboptions_for_category(self, category: str) -> List[str]:
        """Get suboptions for a category."""
        suboptions_map = {
            "oven": ["-", "met pyrolyse", "zonder pyrolyse"],
            "vaatwasser": ["-", "lade", "mandje"]
        }
        return suboptions_map.get(category, ["-"])

    def update_blocks(self, blocks: Dict[str, ElectricBlock]):
        """Update available blocks."""
        block_names = list(blocks.keys())
        self.block_menu.configure(values=block_names)
        if block_names:
            self.block_var.set(block_names[0])

    def update_categories(self, categories: List[str]):
        """Update available categories."""
        self.category_menu.configure(values=categories)
        if categories:
            self.category_var.set(categories[0])

    def update_brands(self, brands: List[str]):
        """Update available brands."""
        self.brand_menu.configure(values=brands)
        if brands:
            self.brand_var.set(brands[0])

    def get_current_vat_rate(self) -> float:
        """Get current VAT rate."""
        return self.config.vat_rates["low"] if self.vat_switch.get() else self.config.vat_rates["high"]


class ApplianceRow(ctk.CTkFrame):
    """Individual appliance row component."""

    def __init__(self, master, appliance: Appliance, image_cache: ImageCache,
                 vat_rate: float, on_add_to_cart: Callable):
        super().__init__(master)
        self.appliance = appliance
        self.image_cache = image_cache
        self.vat_rate = vat_rate
        self.on_add_to_cart = on_add_to_cart

        self._build_ui()

    def _build_ui(self):
        """Build the appliance row UI."""
        self.grid_columnconfigure(1, weight=1)

        # Image
        image = self.image_cache.load_image(self.appliance.img)
        img_label = ctk.CTkLabel(self, image=image, text="")
        img_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        # Info
        price_incl_vat = round(self.appliance.price_ex * (1 + self.vat_rate), 2)
        info_text = (f"{self.appliance.brand} {self.appliance.code}\n"
                     f"{self.appliance.points} punten • €{price_incl_vat:.2f}")

        info_label = ctk.CTkLabel(self, text=info_text, anchor="w", justify="left")
        info_label.grid(row=0, column=1, sticky="ew", padx=10, pady=5)

        # Add button
        add_btn = ctk.CTkButton(self, text="+ Toevoegen", width=100,
                                command=lambda: self.on_add_to_cart(self.appliance))
        add_btn.grid(row=0, column=2, padx=5, pady=5)


class ResultsPanel(ctk.CTkScrollableFrame):
    """Center panel showing filtered appliances."""

    def __init__(self, master, image_cache: ImageCache, on_add_to_cart: Callable):
        super().__init__(master)
        self.image_cache = image_cache
        self.on_add_to_cart = on_add_to_cart
        self.appliance_rows: List[ApplianceRow] = []

        self.columnconfigure(0, weight=1)

    def update_appliances(self, appliances: List[Appliance], vat_rate: float):
        """Update displayed appliances."""
        # Clear existing rows
        for row in self.appliance_rows:
            row.destroy()
        self.appliance_rows.clear()

        # Add new rows
        for i, appliance in enumerate(appliances):
            row = ApplianceRow(self, appliance, self.image_cache,
                               vat_rate, self.on_add_to_cart)
            row.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            self.appliance_rows.append(row)

        # Show message if no results
        if not appliances:
            no_results = ctk.CTkLabel(self, text="Geen toestellen gevonden",
                                      font=("Helvetica", 14))
            no_results.grid(row=0, column=0, pady=50)


class CartPanel(ctk.CTkFrame):
    """Right panel showing shopping cart."""

    def __init__(self, master, cart: ShoppingCart):
        super().__init__(master)
        self.cart = cart
        self.cart_items: Dict[str, ctk.CTkFrame] = {}

        self._build_ui()
        self.cart.add_observer(self.update_display)

    def _build_ui(self):
        """Build the cart panel UI."""
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkLabel(self, text="Winkelwagen",
                              font=("Helvetica", 16, "bold"))
        header.grid(row=0, column=0, pady=10)

        # Cart items scrollable frame
        self.cart_frame = ctk.CTkScrollableFrame(self)
        self.cart_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.cart_frame.columnconfigure(0, weight=1)

        # Totals
        self.totals_label = ctk.CTkLabel(self, text="", font=("Helvetica", 12, "bold"))
        self.totals_label.grid(row=2, column=0, pady=10)

        # Action buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=5)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        clear_btn = ctk.CTkButton(btn_frame, text="Wissen",
                                  command=self.cart.clear)
        clear_btn.grid(row=0, column=0, padx=2, pady=2, sticky="ew")

        export_btn = ctk.CTkButton(btn_frame, text="Exporteren",
                                   command=self._export_cart)
        export_btn.grid(row=0, column=1, padx=2, pady=2, sticky="ew")

    def update_display(self):
        """Update cart display."""
        # Clear existing items
        for widget in self.cart_items.values():
            widget.destroy()
        self.cart_items.clear()

        # Add current items
        for i, item in enumerate(self.cart.items):
            item_frame = self._create_cart_item_widget(item)
            item_frame.grid(row=i, column=0, sticky="ew", padx=2, pady=1)
            self.cart_items[item.appliance.code] = item_frame

        # Update totals (will be called from main app with current VAT rate)

    def _create_cart_item_widget(self, item: CartItem) -> ctk.CTkFrame:
        """Create widget for cart item."""
        frame = ctk.CTkFrame(self.cart_frame)
        frame.columnconfigure(0, weight=1)

        # Item info
        text = f"{item.appliance.code}\n{item.appliance.points}p"
        if item.quantity > 1:
            text += f" (x{item.quantity})"

        info_label = ctk.CTkLabel(frame, text=text, anchor="w")
        info_label.grid(row=0, column=0, sticky="w", padx=5, pady=2)

        # Remove button
        remove_btn = ctk.CTkButton(frame, text="✕", width=30, height=25,
                                   command=lambda: self.cart.remove_item(item.appliance))
        remove_btn.grid(row=0, column=1, padx=2, pady=2)

        return frame

    def update_totals(self, vat_rate: float, max_points: int):
        """Update totals display with current VAT rate and block limit."""
        total_points = self.cart.get_total_points()
        total_price = self.cart.get_total_price(vat_rate)
        remaining_points = max_points - total_points

        # Color coding for remaining points
        if remaining_points >= 0:
            color = "#4CAF50"  # Green
            status = f"Resterend: {remaining_points}p"
        else:
            color = "#F44336"  # Red
            status = f"Overschrijding: {abs(remaining_points)}p"

        totals_text = (f"Totaal: {total_points}p • €{total_price:.2f}\n{status}")
        self.totals_label.configure(text=totals_text, text_color=color)

    def _export_cart(self):
        """Export cart contents (placeholder for future implementation)."""
        # This could export to PDF, Excel, etc.
        logging.getLogger(__name__).info("Export cart functionality not yet implemented")


# ============================================================================
# Main Application
# ============================================================================

class ApplianceManagerApp(ctk.CTkFrame):
    """Main application frame coordinating all components."""

    def __init__(self, master: ctk.CTk = None):
        super().__init__(master)

        # Initialize configuration and services
        self.config = AppConfig()
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        # Initialize data services
        self.repository = JSONDataRepository(self.config)
        self.image_cache = ImageCache(self.config)
        self.cart = ShoppingCart()

        # Load data
        self.blocks = self.repository.load_blocks()
        self.appliances = self.repository.load_appliances()
        self.appliance_filter = ApplianceFilter(self.appliances)

        # Initialize UI
        self._setup_layout()
        self._build_ui()
        self._initialize_data()

        self.logger.info("Application initialized successfully")

    def setup_logging(self):
        """Setup application logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config.base_dir / 'app.log'),
                logging.StreamHandler()
            ]
        )

    def _setup_layout(self):
        """Setup the main layout."""
        self.grid(sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=0, minsize=250)  # Filter panel
        self.columnconfigure(1, weight=3)  # Results panel
        self.columnconfigure(2, weight=1, minsize=300)  # Cart panel

    def _build_ui(self):
        """Build the main UI components."""
        # Filter panel
        self.filter_panel = FilterPanel(self, self.config, self._on_filter_change)
        self.filter_panel.grid(row=0, column=0, sticky="nsew", padx=(5, 2), pady=5)

        # Results panel
        self.results_panel = ResultsPanel(self, self.image_cache, self._on_add_to_cart)
        self.results_panel.grid(row=0, column=1, sticky="nsew", padx=2, pady=5)

        # Cart panel
        self.cart_panel = CartPanel(self, self.cart)
        self.cart_panel.grid(row=0, column=2, sticky="nsew", padx=(2, 5), pady=5)

    def _initialize_data(self):
        """Initialize UI with data."""
        # Update filter panel with available data
        self.filter_panel.update_blocks(self.blocks)

        categories = sorted(set(a.category for a in self.appliances))
        self.filter_panel.update_categories(categories)

        # Initial filter
        self._on_filter_change()

    def _on_filter_change(self):
        """Handle filter changes."""
        try:
            # Get current filter values
            selected_block = self.filter_panel.block_var.get()
            category = self.filter_panel.category_var.get()
            brand = self.filter_panel.brand_var.get()
            suboption = self.filter_panel.suboption_var.get()
            search_term = self.filter_panel.search_var.get().strip()

            # Get block limits
            max_points = None
            if selected_block in self.blocks:
                max_points = self.blocks[selected_block].max_points

            # Update available brands for current category and block
            available_brands = self.appliance_filter.get_brands_for_category(
                category, max_points)
            self.filter_panel.update_brands(available_brands)

            # Filter appliances
            filtered_appliances = self.appliance_filter.filter(
                category=category,
                brand=brand,
                option=suboption,
                max_points=max_points,
                search_term=search_term if search_term else None
            )

            # Update results panel
            vat_rate = self.filter_panel.get_current_vat_rate()
            self.results_panel.update_appliances(filtered_appliances, vat_rate)

            # Update cart totals
            if max_points is not None:
                self.cart_panel.update_totals(vat_rate, max_points)

            self.logger.debug(f"Filter applied: {len(filtered_appliances)} results")

        except Exception as e:
            self.logger.error(f"Error applying filter: {e}")

    def _on_add_to_cart(self, appliance: Appliance):
        """Handle adding appliance to cart."""
        try:
            self.cart.add_item(appliance)
            self.logger.info(f"Added {appliance.code} to cart")

            # Update totals after adding item
            selected_block = self.filter_panel.block_var.get()
            if selected_block in self.blocks:
                max_points = self.blocks[selected_block].max_points
                vat_rate = self.filter_panel.get_current_vat_rate()
                self.cart_panel.update_totals(vat_rate, max_points)

        except Exception as e:
            self.logger.error(f"Error adding item to cart: {e}")


# ============================================================================
# Application Window
# ============================================================================

class LoadingFrame(ctk.CTkFrame):
    """Simple loading screen with progress bar and logo."""

    def __init__(self, master: ctk.CTk):
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure((0, 1, 2), weight=1)

        logo_img = ctk.CTkImage(Image.open(LOGO_IMAGE_PATH), size=(150, 45))
        ctk.CTkLabel(self, image=logo_img, text="").grid(row=0, column=0, pady=(20, 10))
        ctk.CTkLabel(self, text="Toestellenmanager laden...", font=("Helvetica", 16)).grid(row=1, column=0)

        self.progress = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress.grid(row=2, column=0, sticky="ew", padx=40, pady=(10, 20))

    def start(self):
        self.progress.start()

    def stop(self):
        self.progress.stop()


class ApplianceManagerWindow(ctk.CTkToplevel):
    """Main application window."""

    def __init__(self, master: ctk.CTk = None):
        super().__init__(master)
        self.icon_image = tk.PhotoImage(file=LOGO_IMAGE_PATH)
        self.iconphoto(False, self.icon_image)

        self.title("Ixina Toestellenmanager v2.0")

        # Temporary small window while loading
        self.geometry("400x200")
        self.resizable(False, False)

        # Container frame managed by grid for consistent layout
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.container = ctk.CTkFrame(self)
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        loader = LoadingFrame(self.container)
        loader.grid(row=0, column=0, sticky="nsew")
        loader.start()
        self.update_idletasks()

        # Perform heavy initialization
        self.app = ApplianceManagerApp(self.container)

        loader.stop()
        loader.destroy()

        # Final window size
        self.geometry("1400x800")
        self.minsize(1000, 600)

        # Center window
        self.after(10, self._center_window)

        # Setup window protocols
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _center_window(self):
        """Center the window on screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() - width) // 2
        y = (self.winfo_screenheight() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.focus_force()

    def _on_closing(self):
        """Handle window closing."""
        logging.getLogger(__name__).info("Application closing")
        self.destroy()


# ============================================================================
# Unit Tests Examples
# ============================================================================

def test_appliance_from_dict():
    """Test Appliance creation from dictionary."""
    data = {
        'code': 'TEST001',
        'brand': 'TestBrand',
        'category': 'oven',
        'punten': 50,
        'price_ex': 499.99,
        'option': 'met pyrolyse',
        'img': 'test.jpg'
    }

    appliance = Appliance.from_dict(data)
    assert appliance.code == 'TEST001'
    assert appliance.points == 50
    assert appliance.price_ex == 499.99


def test_shopping_cart():
    """Test shopping cart functionality."""
    cart = ShoppingCart()
    appliance = Appliance('TEST001', 'TestBrand', 'oven', 50, 499.99)

    # Test adding items
    cart.add_item(appliance)
    assert len(cart.items) == 1
    assert cart.get_total_points() == 50

    # Test adding same item (should increase quantity)
    cart.add_item(appliance)
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 2
    assert cart.get_total_points() == 100

    # Test removing items
    cart.remove_item(appliance)
    assert len(cart.items) == 0
    assert cart.get_total_points() == 0


def test_appliance_filter():
    """Test appliance filtering."""
    appliances = [
        Appliance('OVEN001', 'Siemens', 'oven', 60, 599.99),
        Appliance('KOOK001', 'Bosch', 'kookplaat', 40, 399.99),
        Appliance('VAAS001', 'Miele', 'vaatwasser', 80, 799.99)
    ]

    filter_obj = ApplianceFilter(appliances)

    # Test category filter
    ovens = filter_obj.filter(category='oven')
    assert len(ovens) == 1
    assert ovens[0].code == 'OVEN001'

    # Test points filter
    low_points = filter_obj.filter(max_points=50)
    assert len(low_points) == 2

    # Test brand filter
    siemens = filter_obj.filter(brand='Siemens')
    assert len(siemens) == 1
    assert siemens[0].brand == 'Siemens'


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main application entry point."""
    # Set CustomTkinter appearance
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # Create and run application
    try:
        app = ApplianceManagerWindow()
        app.mainloop()
    except Exception as e:
        logging.getLogger(__name__).critical(f"Application failed to start: {e}")
        raise


if __name__ == "__main__":
    main()
