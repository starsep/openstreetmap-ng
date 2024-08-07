import i18next from "i18next"
import { activityTracking } from "../_config.js"
import { configureStandardForm } from "../_standard-form.js"

const signupBody = document.querySelector("body.signup-body")
if (signupBody) {
    const signupForm = signupBody.querySelector("form.signup-form")
    const trackingInput = signupForm.elements.tracking
    const displayNameInput = signupForm.elements.display_name
    const displayNameBlacklist = displayNameInput.dataset.blacklist
    const emailInput = signupForm.elements.email
    const emailConfirmationInput = signupForm.elements.email_confirm
    const passwordInput = signupForm.elements.password
    const passwordConfirmationInput = signupForm.elements.password_confirm

    trackingInput.value = activityTracking

    const onSignupSuccess = () => {
        location.href = "/user/terms"
    }

    const onClientValidation = () => {
        const result = new Array()

        const displayNameValue = displayNameInput.value
        if (displayNameBlacklist.split("").some((c) => displayNameValue.includes(c))) {
            const msg = i18next.t("validations.url_characters", {
                characters: displayNameBlacklist,
                interpolation: { escapeValue: false },
            })
            result.push({ type: "error", loc: ["", "display_name"], msg })
        }

        if (emailInput.value !== emailConfirmationInput.value) {
            const msg = i18next.t("validation.email_missmatch")
            result.push({ type: "error", loc: ["", "email"], msg })
            result.push({ type: "error", loc: ["", "email_confirm"], msg })
        }

        if (passwordInput.value !== passwordConfirmationInput.value) {
            const msg = i18next.t("validation.password_missmatch")
            result.push({ type: "error", loc: ["", "password"], msg })
            result.push({ type: "error", loc: ["", "password_confirm"], msg })
        }

        return result
    }

    configureStandardForm(signupForm, onSignupSuccess, onClientValidation)
}
