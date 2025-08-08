#!/usr/bin/env python3
"""
Ixina Tools – Toestellenmanager (v2.0, refactored)

Een moderne, robuuste applicatie voor het beheren van keukentoestellen.
Volledig herschreven met focus op onderhoudbaarheid, prestaties en uitbreidbaarheid.
"""

from __future__ import annotations

import json
import logging
import math
from decimal import Decimal, ROUND_HALF_UP
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Callable, Any
from collections import OrderedDict
import tkinter as tk

try:
    import customtkinter as ctk
except ModuleNotFoundError:  # pragma: no cover - allow headless use
    logging.getLogger(__name__).warning(
        "customtkinter not available; using tkinter-based dummies. GUI functionality will be disabled."
    )

    class _DummyVar:
        def __init__(self, value=None):
            self._value = value

        def get(self):
            return self._value

        def set(self, value):
            self._value = value

    class _DummyWidget:
        def __init__(self, *args, **kwargs):
            pass

        def grid(self, *args, **kwargs):
            pass

        def pack(self, *args, **kwargs):
            pass

        def place(self, *args, **kwargs):
            pass

        def configure(self, *args, **kwargs):
            pass

        def bind(self, *args, **kwargs):
            pass

        def destroy(self, *args, **kwargs):
            pass

        def focus_force(self, *args, **kwargs):
            pass

        def after(self, *args, **kwargs):
            pass

        def update(self, *args, **kwargs):
            pass

        def start(self, *args, **kwargs):
            pass

        def stop(self, *args, **kwargs):
            pass

    class _DummyImage:
        def __init__(self, *args, **kwargs):
            pass

    class _CTkModule:
        CTk = _DummyWidget
        CTkFrame = _DummyWidget
        CTkLabel = _DummyWidget
        CTkButton = _DummyWidget
        CTkEntry = _DummyWidget
        CTkOptionMenu = _DummyWidget
        CTkSwitch = _DummyWidget
        CTkScrollableFrame = _DummyWidget
        CTkToplevel = _DummyWidget
        CTkProgressBar = _DummyWidget
        CTkImage = _DummyImage
        StringVar = _DummyVar
        DoubleVar = _DummyVar
        IntVar = _DummyVar
        END = tk.END

        def set_appearance_mode(self, *args, **kwargs):
            pass

        def set_default_color_theme(self, *args, **kwargs):
            pass

    ctk = _CTkModule()

from PIL import Image, ImageDraw, ImageOps, ImageFont

BASE_DIR = Path(__file__).parent
LOGO_IMAGE_PATH = BASE_DIR / "logo.png"

# Predefined appliance categories shown in the UI
CATEGORIES = [
    "afzuigkappen",
    "bakovens",
    "kookplaat",
    "vaatwasser",
    "koelkast",
    "microgolf",
]

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
    description: str
    width_mm: float
    height_mm: float
    depth_mm: float
    points: int
    price: float
    option: Optional[str] = None
    img: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Appliance':
        """Create Appliance from dictionary with validation."""
        required_fields = {
            'code', 'brand', 'category', 'description',
            'width_mm', 'height_mm', 'depth_mm', 'punten', 'price'
        }
        if not all(field in data for field in required_fields):
            raise ValueError(f"Missing required fields in appliance data: {data}")

        return cls(
            code=str(data['code']),
            brand=str(data['brand']),
            category=str(data['category']),
            description=str(data['description']),
            width_mm=float(data['width_mm']),
            height_mm=float(data['height_mm']),
            depth_mm=float(data['depth_mm']),
            points=int(data['punten']),
            price=float(data['price']),
            option=data.get('option'),
            img=data.get('img')
        )

    # ------------------------------------------------------------------
    # Price conversions
    # ------------------------------------------------------------------
    @staticmethod
    def _round_half_up(value: float) -> int:
        return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @property
    def vat_rate(self) -> float:
        """Return VAT rate based on category."""
        return 0.06 if self.category.lower() == "afzuigkappen" else 0.21

    @property
    def internal_price(self) -> int:
        """Internal price including VAT using fixed coefficients."""
        coeff = 0.344 if self.vat_rate == 0.06 else 0.393
        return self._round_half_up(self.points * coeff)

    @property
    def catalog_price(self) -> int:
        """Catalog/site price using €0.685 per point."""
        return self._round_half_up(self.points * 0.685)

    @property
    def price_ex(self) -> float:
        """Return price excluding VAT using internal price."""
        return self.internal_price / (1 + self.vat_rate)

    @staticmethod
    def points_from_catalog_price(price: float) -> int:
        """Calculate points from catalog price so rounding reproduces price."""
        return math.ceil((price - 0.5) / 0.685)


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
        # cache key is (filename, size)
        self.cache: OrderedDict[tuple[Optional[str], tuple[int, int]], ctk.CTkImage] = OrderedDict()
        self.logger = logging.getLogger(__name__)

    def load_image(self, filename: Optional[str] = None,
                   size: Optional[tuple[int, int]] = None) -> ctk.CTkImage:
        """Load and cache image with fallback to placeholder."""
        size = size or self.config.img_size
        key = (filename, size)
        if key in self.cache:
            # move to end to maintain LRU order
            self.cache.move_to_end(key)
            return self.cache[key]

        try:
            if filename:
                img_path = self.config.img_dir / filename
                if img_path.is_file() and self._is_safe_path(img_path):
                    image = Image.open(img_path)
                    image = ImageOps.contain(image, size)
                else:
                    image = self._create_placeholder("Not Found", size)
            else:
                image = self._create_placeholder("No Image", size)

            ctk_image = ctk.CTkImage(image, size=size)
            self.cache[key] = ctk_image
            # enforce cache size limit
            if len(self.cache) > self.config.cache_size:
                self.cache.popitem(last=False)
            return ctk_image

        except Exception as e:
            self.logger.warning(f"Failed to load image {filename}: {e}")
            return self._get_error_image(size)

    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is safe (prevent directory traversal)."""
        try:
            path.resolve().relative_to(self.config.img_dir.resolve())
            return True
        except ValueError:
            return False

    def _create_placeholder(self, text: str, size: tuple[int, int]) -> Image.Image:
        """Create placeholder image with text."""
        image = Image.new("RGB", size, "#444444")
        draw = ImageDraw.Draw(image)

        # Draw simple cross so the placeholder is clearly visible
        w, h = size
        draw.line((0, 0, w, h), fill="white", width=2)
        draw.line((0, h, w, 0), fill="white", width=2)

        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (w - text_width) // 2
        y = (h - text_height) // 2
        draw.text((x, y), text, fill="white", font=font)

        return image

    def _get_error_image(self, size: tuple[int, int]) -> ctk.CTkImage:
        """Return cached error image."""
        key = ("ERROR", size)
        if key not in self.cache:
            self.cache[key] = ctk.CTkImage(
                self._create_placeholder("Error", size),
                size=size,
            )
            if len(self.cache) > self.config.cache_size:
                self.cache.popitem(last=False)
        return self.cache[key]


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
               max_points: Optional[int] = None,
               search_term: Optional[str] = None) -> List[Appliance]:
        """Filter appliances based on criteria."""
        result = self.appliances.copy()

        if category and category != "-":
            result = [a for a in result if a.category == category]

        if brand and brand != "-":
            result = [a for a in result if a.brand == brand]

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
        return ["-"] + brands if brands else ["-"]


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

    def get_total_price(self) -> float:
        """Calculate total internal price including VAT for each item."""
        return sum(item.appliance.internal_price * item.quantity for item in self.items)

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
        self.search_var = ctk.StringVar()

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

    def _setup_callbacks(self):
        """Setup callbacks for UI controls."""
        self.block_var.trace_add("write", lambda *_: self.on_filter_change())
        self.brand_var.trace_add("write", lambda *_: self.on_filter_change())
        self.category_var.trace_add("write", lambda *_: self.on_filter_change())
        self.search_var.trace_add("write", lambda *_: self.on_filter_change())

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
        current = self.brand_var.get()
        self.brand_menu.configure(values=brands)
        if current not in brands and brands:
            self.brand_var.set(brands[0])

class ApplianceRow(ctk.CTkFrame):
    """Individual appliance row component."""

    def __init__(self, master, appliance: Appliance, image_cache: ImageCache,
                 on_add_to_cart: Callable):
        super().__init__(master)
        self.appliance = appliance
        self.image_cache = image_cache
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
        info_text = (
            f"{self.appliance.description} – €{self.appliance.catalog_price} • {self.appliance.points}p\n"
            f"{self.appliance.width_mm:.0f} x {self.appliance.height_mm:.0f} x {self.appliance.depth_mm:.0f} mm"
        )

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
        self.no_results_label: Optional[ctk.CTkLabel] = None

        self.columnconfigure(0, weight=1)

    def update_appliances(self, appliances: List[Appliance]):
        """Update displayed appliances."""
        # Clear existing rows and any previous 'no results' message
        for row in self.appliance_rows:
            row.destroy()
        self.appliance_rows.clear()
        if self.no_results_label is not None:
            self.no_results_label.destroy()
            self.no_results_label = None

        # Add new rows
        for i, appliance in enumerate(appliances):
            row = ApplianceRow(self, appliance, self.image_cache,
                               self.on_add_to_cart)
            row.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            self.appliance_rows.append(row)

        # Show message if no results
        if not appliances:
            self.no_results_label = ctk.CTkLabel(
                self, text="Geen toestellen gevonden", font=("Helvetica", 14)
            )
            self.no_results_label.grid(row=0, column=0, pady=50)


class CartPanel(ctk.CTkFrame):
    """Right panel showing shopping cart."""

    def __init__(self, master, cart: ShoppingCart, image_cache: ImageCache):
        super().__init__(master)
        self.cart = cart
        self.image_cache = image_cache
        self.cart_items: Dict[str, ctk.CTkFrame] = {}
        self.max_points = 0

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

        # Update totals using last known block limit
        self.update_totals(self.max_points)

    def _create_cart_item_widget(self, item: CartItem) -> ctk.CTkFrame:
        """Create widget for cart item."""
        frame = ctk.CTkFrame(self.cart_frame)
        frame.grid_columnconfigure(1, weight=1)

        # Image
        image = self.image_cache.load_image(item.appliance.img, size=(80, 55))
        img_label = ctk.CTkLabel(frame, image=image, text="")
        img_label.grid(row=0, column=0, rowspan=2, padx=5, pady=2)

        # Item info
        info_text = (
            f"{item.appliance.description} – €{item.appliance.catalog_price} • {item.appliance.points}p"
        )
        if item.quantity > 1:
            info_text += f" (x{item.quantity})"
        info_text += (
            f"\n{item.appliance.width_mm:.0f} x {item.appliance.height_mm:.0f} x {item.appliance.depth_mm:.0f} mm"
        )

        info_label = ctk.CTkLabel(frame, text=info_text, anchor="w", justify="left")
        info_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        # Remove button
        remove_btn = ctk.CTkButton(frame, text="✕", width=30, height=25,
                                   command=lambda: self.cart.remove_item(item.appliance))
        remove_btn.grid(row=0, column=2, padx=2, pady=2)

        return frame

    def update_totals(self, max_points: int):
        """Update totals display with block limit."""
        self.max_points = max_points
        total_points = self.cart.get_total_points()
        total_price = self.cart.get_total_price()
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
        # Arrange panels horizontally: filter on the left,
        # results in the center, and cart on the right
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=0)  # Filter panel
        self.columnconfigure(1, weight=1)  # Results panel
        self.columnconfigure(2, weight=0)  # Cart panel

    def _build_ui(self):
        """Build the main UI components."""
        # Filter panel (left)
        self.filter_panel = FilterPanel(self, self.config, self._on_filter_change)
        self.filter_panel.grid(row=0, column=0, sticky="ns", padx=(5, 2), pady=5)

        # Results panel (center)
        self.results_panel = ResultsPanel(self, self.image_cache, self._on_add_to_cart)
        self.results_panel.grid(row=0, column=1, sticky="nsew", padx=2, pady=5)

        # Cart panel (right)
        self.cart_panel = CartPanel(self, self.cart, self.image_cache)
        self.cart_panel.grid(row=0, column=2, sticky="ns", padx=(2, 5), pady=5)

    def _initialize_data(self):
        """Initialize UI with data."""
        # Update filter panel with available data
        self.filter_panel.update_blocks(self.blocks)

        categories = CATEGORIES
        self.filter_panel.update_categories(categories)

        # Select first category that has appliances so results are visible
        for cat in categories:
            if self.appliance_filter.by_category.get(cat):
                self.filter_panel.category_var.set(cat)
                break

        # Initial filter
        self._on_filter_change()

    def _on_filter_change(self):
        """Handle filter changes."""
        try:
            # Get current filter values
            selected_block = self.filter_panel.block_var.get()
            category = self.filter_panel.category_var.get()
            search_term = self.filter_panel.search_var.get().strip()

            # Get block limits
            max_points = None
            if selected_block in self.blocks:
                max_points = self.blocks[selected_block].max_points

            # Update available brands for current category and block
            available_brands = self.appliance_filter.get_brands_for_category(
                category, max_points)
            self.filter_panel.update_brands(available_brands)

            # Read brand again after updating the dropdown
            brand = self.filter_panel.brand_var.get()

            # Filter appliances
            filtered_appliances = self.appliance_filter.filter(
                category=category,
                brand=brand,
                max_points=max_points,
                search_term=search_term if search_term else None
            )

            # Update results panel
            self.results_panel.update_appliances(filtered_appliances)

            # Update cart totals
            if max_points is not None:
                self.cart_panel.update_totals(max_points)

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
                self.cart_panel.update_totals(max_points)

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

        # use a grid container so loader and main app use the same geometry manager
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.container = ctk.CTkFrame(self)
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        loader = LoadingFrame(self.container)
        loader.grid(row=0, column=0, sticky="nsew")
        loader.start()
        self.update()

        # Perform heavy initialization
        self.app = ApplianceManagerApp(self.container)

        loader.stop()
        loader.destroy()

        # ensure main application fills the window from the top
        self.app.grid(row=0, column=0, sticky="nsew")

        # Final window size
        self.geometry("1400x800")
        self.minsize(1000, 600)
        self.resizable(True, True)

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
