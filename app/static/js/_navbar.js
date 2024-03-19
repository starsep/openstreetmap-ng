import { Tooltip } from "bootstrap"
import { qsEncode } from "./_qs.js"
import { configureRemoteEditButton } from "./_remote-edit.js"
import "./_types.js"
import { encodeMapState } from "./leaflet/_map-utils.js"

const minEditZoom = 13
const navbar = document.querySelector(".navbar")
const editGroup = navbar.querySelector(".edit-group")
const loginLinks = navbar.querySelectorAll("a[href='/login']")
const loginLinkQuery = qsEncode({ referer: location.pathname })

// Configure the remote edit button (JOSM)
const remoteEditButton = navbar.querySelector(".remote-edit")
if (remoteEditButton) configureRemoteEditButton(remoteEditButton)

// Add active class to current nav-lik
const navLinks = navbar.querySelectorAll(".nav-link")
for (const link of navLinks) {
    if (link.getAttribute("href") === location.pathname) {
        link.classList.add("active")
        link.ariaCurrent = "page"
        break
    }
}

/**
 * Map of navbar elements to their base href
 * @type {Map<HTMLElement, string>}
 */
const mapLinksHrefMap = Array.from(navbar.querySelectorAll(".map-link")).reduce(
    (map, link) => map.set(link, link.getAttribute("href")),
    new Map(),
)

// TODO: wth object support?
/**
 * Update the navbar links and current URL hash
 * @param {MapState} state Map state object
 * @param {OSMObject|null} object Optional OSM object
 * @returns {void}
 */
export const updateNavbarAndHash = (state, object = null) => {
    const isEditDisabled = state.zoom < minEditZoom
    const hash = encodeMapState(state)

    const loginHref = `/login?${loginLinkQuery}${hash}`
    for (const link of loginLinks) link.href = loginHref

    for (const [link, baseHref] of mapLinksHrefMap) {
        const isEditLink = link.classList.contains("edit-link")
        if (isEditLink) {
            // Remote edit button stores information in dataset
            const isRemoteEditButton = link.classList.contains("remote-edit-btn")
            if (isRemoteEditButton) {
                link.dataset.remoteEdit = JSON.stringify({ state, object })
            } else if (object) {
                link.href = `${baseHref}?${object.type}=${object.id}${hash}`
            } else {
                link.href = baseHref + hash
            }

            // Enable/disable edit links based on current zoom level
            if (isEditDisabled) {
                if (!link.classList.contains("disabled")) {
                    link.classList.add("disabled")
                    link.ariaDisabled = "true"
                }
            } else {
                // biome-ignore lint/style/useCollapsedElseIf: Readability
                if (link.classList.contains("disabled")) {
                    link.classList.remove("disabled")
                    link.ariaDisabled = "false"
                }
            }
        } else {
            link.href = baseHref + hash
        }
    }

    // Toggle tooltip on edit group
    if (isEditDisabled) {
        if (!editGroup.classList.contains("disabled")) {
            editGroup.classList.add("disabled")
            editGroup.ariaDisabled = "true"
            Tooltip.getOrCreateInstance(editGroup, {
                title: editGroup.dataset.bsTitle,
                placement: "bottom",
            }).enable()
        }
    } else {
        // biome-ignore lint/style/useCollapsedElseIf: Readability
        if (editGroup.classList.contains("disabled")) {
            editGroup.classList.remove("disabled")
            editGroup.ariaDisabled = "false"
            Tooltip.getInstance(editGroup).disable()
        }
    }

    history.replaceState(null, "", hash)
}

// On window mapState message, update the navbar and hash
const onMapState = (data) => {
    const { lon, lat, zoom } = data.state
    updateNavbarAndHash({ lon, lat, zoom: Math.floor(zoom), layersCode: "" })
}

// Handle mapState window messages (from iD/Rapid)
addEventListener("message", (event) => {
    const data = event.data
    if (data.type === "mapState") onMapState(data)
})
