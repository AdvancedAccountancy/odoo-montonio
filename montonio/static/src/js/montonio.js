odoo.define('payment_montonio.montonio', function(require) {
    var ajax = require('web.ajax');
    var core = require('web.core');
    
    /**
    * Global translation method
    */
    var _t = core._t;
    
    /**
    * Odoo templating engine and get error message template
    */
    var qweb = core.qweb;
    ajax.loadXML('/montonio/static/src/xml/montonio_templates.xml', qweb);
    
    /**
    * This contains the last <form> created by when pressing 'Pay Now'
    */
    var providerForm = null;
    
    /**
    * Draft token from Montonio API after submitting draft
    */
    var $DRAFTTOKEN = null;
    
    /**
    * The environment to use for Montonio iframe 
    */
    var $ENVIRONMENT = 'production';
    
    /**
    * Translations for error messages
    */
    var translations = {
        'en': {
            MSG_UNKNOWN: 'An unknown error occurred. The payment was not processed. Please contact support at info@montonio.com for more details.',
            MSG_NO_DRAFTTOKEN: 'Unable to initiate Montonio payment. The payment was not processed. Please contact support at info@montonio.com.',
            MSG_APPLICATION_FAILED: 'Unfortunately, no application was signed through Montonio. The payment has not been processed. Check your email for more details or contact us at info@montonio.com',
            MSG_STATUS_CHECK_FAILED: 'An unknown error occurred when checking Montonio application status. Please contact the merchant to check if your order was processed or contact us at info@montonio.com',
            MSG_APPLICATION_SIGNED_TITLE: 'Success! The payment has been accepted and your order is going to be fulfilled. <br><br>Thank you for using Montonio.'
        },
        'et': {
            MSG_UNKNOWN: 'Tekkis tundmatu viga. Makse ei õnnestunud. Rohkema info saamiseks palun pöörduge Montonio klienditeeninduse poole e-mailil info@montonio.com',
            MSG_NO_DRAFTTOKEN: 'Montoniol ei õnnestunud makseprotsessi alustada. Tellimus jäi lõpetamata. Rohkema info saamiseks palun pöörduge Montonio klienditeeninduse poole e-mailil info@montonio.com',
            MSG_APPLICATION_FAILED: 'Kahjuks ei sõlmitud Montonio kaudu ühtegi laenulepingut. Tellimus tühistatakse.  Rohkema info saamiseks palun pöörduge Montonio klienditeeninduse poole e-mailil info@montonio.com',
            MSG_STATUS_CHECK_FAILED: 'Tekkis tundmatu viga laenutaotluse staatuse küsimisel Montonio süsteemist. Palun kontakteeruge kaupmehega, et teada saada, kas Teie tellimus läks läbi või võtke ühendust Montonio klienditeenindusega e-mailil info@montonio.com',
            MSG_APPLICATION_SIGNED_TITLE: 'Palju õnne! Teie järelmaksuleping on sõlmitud. Teie tellimus on vastu võetud ja läheb täitmisele.<br><br>Aitäh, et valisite Montonio.'
        }
    }
    
    /**
    * The language to use for error messages
    */
    var $lang = 'et';
    
    /**
    * Observe changes in html and call createDraft()
    */
    var observer = new MutationObserver(function(mutations, observer) {
        for(var i=0; i<mutations.length; ++i) {
            for(var j=0; j<mutations[i].addedNodes.length; ++j) {
                if(mutations[i].addedNodes[j].tagName.toLowerCase() === "form" && mutations[i].addedNodes[j].getAttribute('provider') == 'montonio') {
                    createDraft($(mutations[i].addedNodes[j]));
                }
            }
        }
    });
    
    /**
    * Get Montonio SDK, start observer,
    * and call createDraft() for the first time
    */
    $.getScript("https://public.montonio.com/assets/js/production/montonio-sdk.min.js", function (data, textStatus, jqxhr) { 
    observer.observe(document.body, {childList: true});
    createDraft($('form[provider="montonio"]'));}
    );
    
    /**
    * Post draft to Montonio API, get DRAFTTOKEN and init Montonio
    * @param {HTMLElement} form 
    */
    function createDraft(form) {
        providerForm = form;
        
        if (providerForm) {
            
            $('#o_payment_form_pay').prop('disabled', true);

            // check that invoice number exists
            var invoiceField = _get_input_value('invoice_num');
            
            if (invoiceField) {
                // make request to Montonio API
                ajax.jsonRpc("/payment/montonio/create_draft", 'call', {
                    invoice_num: invoiceField,
                    customer_city: _get_input_value('customer_city'),
                    customer_email: _get_input_value('customer_email'),
                    customer_phone: _get_input_value('customer_phone'),
                    customer_address: _get_input_value('customer_address'),
                    customer_last_name: _get_input_value('customer_last_name'),
                    customer_first_name: _get_input_value('customer_first_name'),
                    customer_postal_code: _get_input_value('customer_postal_code')
                })
                .always(function(response){
                    try {
                        var parsed = JSON.parse(response);
                        if (parsed.status == 'SUCCESS') { 
                            
                            // set $DRAFTTOKEN and init Montonio modal
                            $DRAFTTOKEN = parsed.data.access_token;
                            registerWindowFunctions();
                            initMontonio(); 
                        }
                        // throw if draft token submission failed for some reason
                        else throw new Error()
                    } 
                    // Unexpected error occurred or failed to make draft
                    catch (err) {
                        failGracefully(translations[$lang]['MSG_NO_DRAFTTOKEN']); // No draft token, show error
                    }
                    
                })
            } else {
                $('#o_payment_form_pay').prop('disabled', false);
            }
        }
    }
    
    function registerWindowFunctions() {
        
        /**
        * Make call to controller to update invoice status in backend
        * and get URL to redirect to after pressing 
        * "Return to Merchant"
        */
        window.updateMerchantSystem = function () {
            ajax.jsonRpc("/payment/montonio/validate", 'call', {
                invoice_num: _get_input_value('invoice_num')
            })
            .always(function(response) {
                try {
                    console.log('RESPONSE', response)
                    var parsed = JSON.parse(response);
                    switch (parsed.status) {
                        case 'SUCCESS':
                        window.montonio_complete_url = parsed.data
                        break;
                        
                        case 'APPLICATION_ERROR': break; // let montonio handle the error
                        
                        case 'HTTPError':
                        case 'URLError':
                        throw new Error(translations[$lang]['MSG_STATUS_CHECK_FAILED']);
                        
                        default:
                        throw new Error(translations[$lang]['MSG_UNKNOWN']);
                    }
                } catch (err) {
                    failGracefully(err.message)
                }
            })
        }
        
        /**
        * Function that gets called when verdict has been received,
        * merchant system should be updated already and user should
        * be redirected to "success/failure" page
        */
        window.completedFunction = function () {
            if (window.montonio_complete_url) {
                window.location = window.montonio_complete_url
            } else {
                Montonio.closeModal();
                Montonio.removeBackdrop();
            }
        }
        
        /**
        * Close modal when user closes gateway without verdict
        */
        window.userClosedGateway = function () {
            Montonio.removeBackdrop();
        }
    }
    
    // Montonio flow
    function initMontonio() {
        
        // Register Montonio callback functions 
        if ($DRAFTTOKEN && Montonio) {
            Montonio.init();
            Montonio.setEnvironment($ENVIRONMENT);
            Montonio.prepareDraftToken($DRAFTTOKEN);
            Montonio.addBackdrop();
            Montonio.openModal();
            $('#o_payment_form_pay').prop('disabled', false);
        }
    }
    
    /**
    * Function that shows error popup in odoo 
    * @param {string} message 
    */
    function failGracefully(message) {
        var wizard = $(qweb.render('montonio.error', { 'msg': message || _t('Payment error') }));
        wizard.appendTo($('body')).modal({ 'keyboard': true });
        $('#o_payment_form_pay').prop('disabled', false);
    }
    
    /**
    * Helper function to get value from providerForm input
    * @param {string} name input name
    */
    function _get_input_value(name) {
        if (providerForm) {
            return providerForm.find('input[name="' + name + '"]').val();
        }
        else return null;
    }
    
});
