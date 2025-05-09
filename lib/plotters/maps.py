import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import contextily as ctx


class Map:
    def __init__(self, figsize=(10, 15), extent=[-130, -30, -60, 40]):
        self.fig, self.ax = plt.subplots(
            figsize=figsize, subplot_kw={"projection": ccrs.PlateCarree()}
        )
        self.ax.set_extent(extent, crs=ccrs.PlateCarree())
        self.scatter_data = []
        self.feature_data = []
        self.sat_img_data = []

    def add_scatter(
        self,
        lon,
        lat,
        s=35,
        facecolor="blue",
        edgecolor="blue",
        marker="^",
        zorder=1,
        label="",
        **kwargs
    ):
        self.ax.scatter(
            lon,
            lat,
            s=s,
            facecolor=facecolor,
            edgecolor=edgecolor,
            marker=marker,
            zorder=zorder,
            label=label,
            **kwargs
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
                **kwargs
            }
        )

    def add_gdf(
        self,
        gdf,
        column="NOMBRE",
        color_map="viridis",
        **kwargs
    ):
        # Verificar si la geometría contiene diferentes tipos y representarlos adecuadamente
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
                    # Dibujar puntos
                    self.ax.scatter(
                        geom.x,
                        geom.y,
                        facecolor=color,
                        label=val,
                        transform=ccrs.PlateCarree(),
                        **kwargs
                    )
                elif geom.geom_type in ["Polygon", "MultiPolygon"]:
                    # Dibujar polígonos y multipolígonos
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
                            **kwargs
                        )
                elif geom.geom_type in ["LineString", "MultiLineString"]:
                    # Dibujar líneas y multilíneas
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
                            **kwargs
                        )

    def add_features(self, linestyle="-", linewidth=0.5, color="gray", **kwargs):
        self.ax.add_feature(
            cfeature.COASTLINE, linestyle=linestyle, linewidth=linewidth, color=color, **kwargs
        )
        self.ax.add_feature(
            cfeature.BORDERS, linestyle=linestyle, linewidth=linewidth, color=color, **kwargs
        )
        self.ax.add_feature(
            cfeature.LAND, linestyle=linestyle, linewidth=linewidth, color=color, **kwargs
        )
        self.feature_data.append(
            {"linestyle": linestyle, "linewidth": linewidth, "color": color, **kwargs}
        )

    def add_sat_img(self, zoom=5, alpha=1, attribution_size=5, **kwargs):
        ctx.add_basemap(
            self.ax,
            crs=ccrs.PlateCarree(),
            source=ctx.providers.Esri.WorldImagery,
            zoom=zoom,
            alpha=alpha,
            attribution_size=attribution_size,
            **kwargs
        )
        self.sat_img_data.append(
            {"zoom": zoom, "alpha": alpha, "attribution_size": attribution_size, **kwargs}
        )

    def add_gridlines(self, draw_labels=True, color="white", alpha=0.2, **kwargs):
        self.ax.gridlines(draw_labels=draw_labels, color=color, alpha=alpha, **kwargs)

    def add_legend(self, loc="upper right", facecolor="white", framealpha=1, **kwargs):
        handles, labels = self.get_legend_handles_labels()
        unique_labels = dict(zip(labels, handles))
        self.ax.legend(
            handles=unique_labels.values(),
            labels=unique_labels.keys(),
            loc=loc,
            facecolor=facecolor,
            framealpha=framealpha,
            **kwargs
        )

    def get_legend_handles_labels(self, **kwargs):
        return self.ax.get_legend_handles_labels(**kwargs)

    def tight_layout(self, **kwargs):
        self.fig.tight_layout(**kwargs)

    def save_svg(self, filename="mapa.svg", **kwargs):
        self.fig.savefig(filename, format="svg", **kwargs)

    def save_png(self, filename="mapa.png", format="png", dpi=300, **kwargs):
        self.fig.savefig(filename, format=format, dpi=dpi, **kwargs)

    def add_inset_axes(self, bounds, xlim, ylim, zoom_in, att_in, boundcolor="white", **kwargs):
        axin = self.ax.inset_axes(bounds, projection=ccrs.PlateCarree())
        axin.spines["geo"].set_edgecolor(boundcolor)

        for data in self.feature_data:
            axin.add_feature(
                cfeature.COASTLINE,
                linestyle=data["linestyle"],
                linewidth=data["linewidth"],
                color=data["color"],
                **kwargs
            )
            axin.add_feature(
                cfeature.BORDERS,
                linestyle=data["linestyle"],
                linewidth=data["linewidth"],
                color=data["color"],
                **kwargs
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
                **kwargs
            )

        axin.set_xlim(xlim, **kwargs)
        axin.set_ylim(ylim, **kwargs)

        data = self.sat_img_data[0]
        ctx.add_basemap(
            axin,
            crs=ccrs.PlateCarree(),
            source=ctx.providers.Esri.WorldImagery,
            zoom=zoom_in,
            alpha=data["alpha"],
            attribution_size=att_in,
            **kwargs
        )
        self.ax.indicate_inset_zoom(axin, edgecolor=boundcolor, **kwargs)
        axin.set_xticklabels([], **kwargs)
        axin.set_yticklabels([], **kwargs)

    def show(self):
        plt.show()
