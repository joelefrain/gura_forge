import contextily as ctx
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import cartopy.feature as cfeature

from modules.plotter.base_plotter import BasePlotter
from libs.config.config_plot import PlotConfig, PlotType, LegendPosition


class Map(BasePlotter):
    def __init__(
        self,
        extent: list = [-130, -30, -60, 40],
        **kwargs,
    ):
        """
        Inicializa el mapa.

        Args:
            extent (list): Límites del mapa [lon_min, lon_max, lat_min, lat_max].
        """
        self.extent = extent

        self.scatter_data = []
        self.feature_data = []
        self.sat_img_data = []

        super().__init__(**kwargs)

    def _initialize_plot(self, **kwargs):
        """Inicializa la figura con proyección cartográfica."""
        self.fig, self.ax = plt.subplots(
            figsize=self.figsize, subplot_kw={"projection": ccrs.PlateCarree()}
        )
        self.ax.set_extent(self.extent, crs=ccrs.PlateCarree())

        self.plot_config = PlotConfig(
            plot_type=PlotType.MAP,
            legend_position=LegendPosition.OUTSIDE_RIGHT,
            **kwargs,
        )
        self.plot_config.register(self.ax)

    def add_scatter(
        self,
        lon,
        lat,
        s: int = 35,
        facecolor: str = "blue",
        edgecolor: str = "blue",
        marker: str = "^",
        zorder: int = 1,
        label: str = "",
        **kwargs,
    ):
        """Añade puntos de dispersión al mapa."""
        self.ax.scatter(
            lon,
            lat,
            s=s,
            facecolor=facecolor,
            edgecolor=edgecolor,
            marker=marker,
            zorder=zorder,
            label=label,
            **kwargs,
        )
        self.scatter_data.append(
            {
                "lon": lon,
                "lat": lat,
                "s": s,
                "facecolor": facecolor,
                "edgecolor": edgecolor,
                "marker": marker,
                "zorder": zorder,
                "label": label,
                **kwargs,
            }
        )

    def add_gdf(
        self, gdf, column: str = "NOMBRE", color_map: str = "viridis", **kwargs
    ):
        """Añade un GeoDataFrame al mapa."""
        unique_values = gdf[column].unique()
        color_dict = {
            val: plt.cm.get_cmap(color_map)(i / len(unique_values))
            for i, val in enumerate(unique_values)
        }

        for val in unique_values:
            subset = gdf[gdf[column] == val]
            color = color_dict[val]

            for geom in subset.geometry:
                if geom.geom_type == "Point":
                    self.ax.scatter(
                        geom.x,
                        geom.y,
                        facecolor=color,
                        label=val,
                        transform=ccrs.PlateCarree(),
                        **kwargs,
                    )
                elif geom.geom_type in ["Polygon", "MultiPolygon"]:
                    for polygon in (
                        geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
                    ):
                        x, y = polygon.exterior.xy
                        self.ax.plot(
                            x,
                            y,
                            color=color,
                            label=val,
                            transform=ccrs.PlateCarree(),
                            **kwargs,
                        )
                elif geom.geom_type in ["LineString", "MultiLineString"]:
                    for line in (
                        geom.geoms if geom.geom_type == "MultiLineString" else [geom]
                    ):
                        x, y = line.xy
                        self.ax.plot(
                            x,
                            y,
                            color=color,
                            label=val,
                            transform=ccrs.PlateCarree(),
                            **kwargs,
                        )

    def add_features(
        self,
        linestyle: str = "-",
        linewidth: float = 0.5,
        color: str = "gray",
        **kwargs,
    ):
        """Añade características geográficas (costas, fronteras, tierra)."""
        self.ax.add_feature(
            cfeature.COASTLINE,
            linestyle=linestyle,
            linewidth=linewidth,
            color=color,
            **kwargs,
        )
        self.ax.add_feature(
            cfeature.BORDERS,
            linestyle=linestyle,
            linewidth=linewidth,
            color=color,
            **kwargs,
        )
        self.ax.add_feature(
            cfeature.LAND,
            linestyle=linestyle,
            linewidth=linewidth,
            color=color,
            **kwargs,
        )
        self.feature_data.append(
            {"linestyle": linestyle, "linewidth": linewidth, "color": color, **kwargs}
        )

    def add_sat_img(
        self, zoom: int = 5, alpha: float = 1, attribution_size: int = 5, **kwargs
    ):
        """Añade imagen satelital como mapa base."""
        ctx.add_basemap(
            self.ax,
            crs=ccrs.PlateCarree(),
            source=ctx.providers.Esri.WorldImagery,
            zoom=zoom,
            alpha=alpha,
            attribution_size=attribution_size,
            **kwargs,
        )
        self.sat_img_data.append(
            {
                "zoom": zoom,
                "alpha": alpha,
                "attribution_size": attribution_size,
                **kwargs,
            }
        )

    def add_gridlines(
        self,
        draw_labels: bool = True,
        color: str = "white",
        alpha: float = 0.2,
        **kwargs,
    ):
        """Añade líneas de cuadrícula al mapa."""
        self.ax.gridlines(draw_labels=draw_labels, color=color, alpha=alpha, **kwargs)

    def add_legend(self):
        """Añade leyenda al mapa."""
        self.ax.legend()

    def add_inset_axes(
        self,
        bounds,
        xlim,
        ylim,
        zoom_in: int,
        att_in: int,
        boundcolor: str = "white",
    ):
        """Añade un recuadro de zoom al mapa."""
        axin = self.ax.inset_axes(bounds, projection=ccrs.PlateCarree())
        axin.spines["geo"].set_edgecolor(boundcolor)

        for data in self.feature_data:
            axin.add_feature(
                cfeature.COASTLINE,
                linestyle=data["linestyle"],
                linewidth=data["linewidth"],
                color=data["color"],
            )
            axin.add_feature(
                cfeature.BORDERS,
                linestyle=data["linestyle"],
                linewidth=data["linewidth"],
                color=data["color"],
            )

        for data in self.scatter_data:
            axin.scatter(
                data["lon"],
                data["lat"],
                s=data["s"],
                facecolor=data["facecolor"],
                edgecolor=data["edgecolor"],
                marker=data["marker"],
                zorder=data["zorder"],
                label=data["label"],
            )

        axin.set_xlim(xlim)
        axin.set_ylim(ylim)

        if self.sat_img_data:
            data = self.sat_img_data[0]
            ctx.add_basemap(
                axin,
                crs=ccrs.PlateCarree(),
                source=ctx.providers.Esri.WorldImagery,
                zoom=zoom_in,
                alpha=data["alpha"],
                attribution_size=att_in,
            )

        self.ax.indicate_inset_zoom(axin, edgecolor=boundcolor)
        axin.set_xticklabels([])
        axin.set_yticklabels([])
